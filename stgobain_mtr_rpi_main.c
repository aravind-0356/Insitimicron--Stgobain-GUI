/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h> //atoi
#include <string.h>
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
#define ENC_RX_BUF_SIZE  16   /* 9-byte Modbus response + margin */
/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
I2C_HandleTypeDef hi2c2;

UART_HandleTypeDef huart5;
UART_HandleTypeDef huart1;
UART_HandleTypeDef huart2;
UART_HandleTypeDef huart3;
DMA_HandleTypeDef hdma_usart1_rx;

/* USER CODE BEGIN PV */
// Holding Registers (4x) - Numerical Data
volatile float raw_displacement = 0.0f;
volatile float tared_displacement = 0.0f;
volatile int16_t motor_speed_setpoint = 100; // Default startup speed

/* ======================================================== */
/* 2. NON-BLOCKING TIMERS                                   */
/* ======================================================== */
uint32_t last_sensor_poll = 0;
uint32_t last_motor_update = 0;
uint32_t last_uart2_tx = 0;

// --- Eurotherm Variables ---
uint8_t eurotherm_rx_buffer[256];
uint8_t eurotherm_rx_index = 0;
uint8_t last_eurotherm_rx_index = 0;
uint8_t eurotherm_rx_byte;
uint8_t eurotherm_state = 0;
uint32_t last_eurotherm_poll = 0;
float eurotherm_temp = 0.0f;

/* ======================================================== */
/* 3. UART RX BUFFERS (For Interrupts)                      */
/* ======================================================== */
// UART2 (Raspberry Pi) Command Ring Buffer
#define UART2_RING_SIZE 256
volatile char uart2_rx_ring[UART2_RING_SIZE];
volatile uint16_t uart2_ring_head = 0;
volatile uint16_t uart2_ring_tail = 0;
uint8_t uart2_rx_byte;

// MicroEpsilon Sensor Variables (Robust Polling)
static float scaled_val = 0.0f;
static float unscaled_val = 0.0f;
static float me_tare_offset = -6.0f; // Tare baseline for fully relaxed position (-6mm offsets to 0mm)
static uint32_t last_me_req_tick = 0;
static uint8_t sensor_rx_buffer[256];
static uint16_t sensor_rx_index = 0;
static uint8_t sensor_rx_byte;
static uint8_t sensor_state = 0;

typedef enum {
    MOTOR_IDLE,
    MOTOR_RUNNING,
    MOTOR_PULLBACK   /* Auto-reverse after break detection, driven by encoder */
} MotorState_t;

MotorState_t current_motor_state = MOTOR_IDLE;
int16_t current_velocity = 100;
uint16_t current_acc = 100; // Default Acceleration
uint16_t current_dec = 100; // Default Deceleration

// Hardware safety flag
bool kill_active = false;

// Command Flags from Pi
volatile bool    pi_cmd_start    = false;
volatile bool    pi_cmd_stop     = false;
volatile bool    pi_cmd_pullback = false;   /* Trigger auto-pullback */

/* ======================================================== */
/* 4. ENCODER VARIABLES (USART1 DMA RX)                     */
/* ======================================================== */
// Pre-built Modbus FC03 request: Slave 0x01, Read 2 regs from 0x602C (high) & 0x602D (low)
static uint8_t  enc_request_frame[8];
// DMA receive buffer — 9 bytes expected (addr + func + byte_count + 4 data + 2 CRC)
static uint8_t  enc_rx_buffer[ENC_RX_BUF_SIZE];
// Latest decoded 32-bit signed encoder position (counts)
volatile int32_t g_encoder_position = 0;
// ISR flags (set in callback, cleared in main loop)
volatile uint8_t g_enc_data_ready = 0;
volatile uint8_t g_enc_crc_fail   = 0;
// Bus arbitration: 1 while a TX+RX transaction is in flight on USART1
// Prevents encoder poll from firing during a motor command sequence
volatile uint8_t encoder_bus_busy  = 0;
static   uint32_t last_enc_poll    = 0;

/* ======================================================== */
/* 5. PULLBACK VARIABLES                                    */
/* ======================================================== */
// PLACEHOLDER: update ENCODER_COUNTS_PER_MM once measured on hardware
#define ENCODER_COUNTS_PER_MM    1000
// Default safe pullback speed (positive = UP). Overridden by PullSpeed: command.
#define PULLBACK_SPEED_DEFAULT   20
static int16_t  pullback_speed_rpm      = PULLBACK_SPEED_DEFAULT;
static int32_t  pullback_target_counts  = 0;   /* Counts to travel */
static int32_t  pullback_start_position = 0;   /* Encoder snapshot at pullback start */

#define KILL_SWITCH_Pin GPIO_PIN_5
#define KILL_SWITCH_Port GPIOB
/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_DMA_Init(void);
static void MX_USART2_UART_Init(void);
static void MX_UART5_Init(void);
static void MX_USART1_UART_Init(void);
static void MX_USART3_UART_Init(void);
static void MX_I2C2_Init(void);
/* USER CODE BEGIN PFP */
void Process_Pi_Commands(void);
void Process_Motor(void);
void Process_Eurotherm(void);
void Process_Sensor(void);
void Process_Encoder(void);
void Process_Motor_TX_Queue(void);
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

// Union removed. Modbus CRC kept for Motor Driver

// Standard Modbus CRC-16 Calculation
uint16_t modbus_crc(uint8_t *data, uint16_t length) {
  uint16_t crc = 0xFFFF;
  for (uint16_t i = 0; i < length; i++) {
    crc ^= data[i];
    for (uint8_t j = 0; j < 8; j++) {
      if (crc & 0x01) crc = (crc >> 1) ^ 0xA001; // MODBUS_POLY
      else crc >>= 1;
    }
  }
  return crc;
}

void append_crc(uint8_t *frame, uint16_t len) {
  uint16_t crc = modbus_crc(frame, len);
  frame[len] = crc & 0xFF;
  frame[len + 1] = (crc >> 8);
}

// NON-BLOCKING MOTOR COMMAND QUEUE
#define MOTOR_TX_QUEUE_SIZE 16
static uint8_t motor_tx_queue[MOTOR_TX_QUEUE_SIZE][8];
static uint8_t motor_tx_head = 0;
static uint8_t motor_tx_tail = 0;
static uint32_t last_motor_tx_tick = 0;
static uint8_t motor_is_txing = 0;

// Enqueue the motor frame instantly and return (Non-Blocking)
void modbus_send_motor(uint8_t *frame, uint16_t len) {
    if ((motor_tx_head + 1) % MOTOR_TX_QUEUE_SIZE != motor_tx_tail) {
        memcpy(motor_tx_queue[motor_tx_head], frame, len); // len is 8
        motor_tx_head = (motor_tx_head + 1) % MOTOR_TX_QUEUE_SIZE;
    }
}

// Background state machine to process motor queue with 5ms delays
void Process_Motor_TX_Queue(void) {
    uint32_t tick = HAL_GetTick();
    
    // If there are frames waiting to be sent
    if (motor_tx_head != motor_tx_tail) {
        // If the bus is completely free, claim it for the motor queue
        if (!encoder_bus_busy && !motor_is_txing) {
            encoder_bus_busy = 1;
            motor_is_txing = 1;
        }
        
        // If we own the bus, send the next frame with a 5ms gap
        if (motor_is_txing) {
            if (tick - last_motor_tx_tick >= 5) {
                // Non-blocking IT transmit. Memory is static (in the queue), so it's safe!
                HAL_UART_Transmit_IT(&huart1, motor_tx_queue[motor_tx_tail], 8);
                motor_tx_tail = (motor_tx_tail + 1) % MOTOR_TX_QUEUE_SIZE;
                last_motor_tx_tick = tick;
            }
        }
    } else {
        // Queue is empty. Release the bus safely after the last frame has had 5ms to settle.
        if (motor_is_txing && (tick - last_motor_tx_tick >= 5)) {
            motor_is_txing = 0;
            encoder_bus_busy = 0;
        }
    }
}

// ---------------------------------------------------------
// DEBUG HELPER — sends a short ASCII string over UART2 (the Pi/serial monitor link)
// All debug lines are prefixed with "DBG:" so they are easy to filter in the monitor.
// MUST be defined before any function that uses it (i.e. before the motor wrappers).
// ---------------------------------------------------------
#define DBG_PRINT(msg) HAL_UART_Transmit(&huart2, (uint8_t*)(msg), sizeof(msg)-1, 20)

// ---------------------------------------------------------
// MOTOR COMMAND WRAPPERS
//
// CS2RS PR-Mode velocity sequence (from User Manual V1.5):
//
//  Step 1 — Write PR Path 0 mode to 0x6200:
//           Value = 0x0012
//           Bit0-3 = 0x2 = velocity mode
//           Bit4   = 1   = INS (interrupt-enabled, required for RS485 motion)
//
//  Step 2 — Write target velocity (RPM) to 0x6203 (Pr9.03)
//
//  Step 3 — Write acceleration to 0x6204 (Pr9.04), unit: ms/1000rpm
//
//  Step 4 — Write deceleration to 0x6205 (Pr9.05), unit: ms/1000rpm
//
//  Step 5 — Trigger motion by writing 0x0010 to PR Control Register 0x6002
//           (Write 0x1P where P=0 = run Path 0)
//
// STOP:
//  Write 0x0040 to 0x6002 = Quick Stop
// ---------------------------------------------------------

void Leadshine_Send_Start(int16_t vel) {
    uint8_t frame[8];

    // --- Frame 1: Set PR Path 0 to Velocity Mode (0x6200 = 0x0012) ---
    // 0x0012 = Bit1(velocity mode) | Bit4(INS=interrupt enabled)
    uint8_t f_mode[6] = {0x01, 0x06, 0x62, 0x00, 0x00, 0x12};
    memcpy(frame, f_mode, 6); append_crc(frame, 6); modbus_send_motor(frame, 8);
    DBG_PRINT("DBG: Frame1 sent -> 0x6200=0x0012 (PR0 velocity mode)\r\n");

    // --- Frame 2: Write velocity (RPM) to 0x6203 (Pr9.03) ---
    uint16_t v = (uint16_t)vel;
    uint8_t f_vel[6] = {0x01, 0x06, 0x62, 0x03, (uint8_t)(v >> 8), (uint8_t)(v & 0xFF)};
    memcpy(frame, f_vel, 6); append_crc(frame, 6); modbus_send_motor(frame, 8);
    {
        char dbg[52];
        int len = snprintf(dbg, sizeof(dbg), "DBG: Frame2 sent -> 0x6203=0x%04X (%d RPM)\r\n", v, vel);
        HAL_UART_Transmit(&huart2, (uint8_t*)dbg, len, 20);
    }

    // --- Frame 3: Write acceleration to 0x6204 (Pr9.04), unit: ms/1000rpm ---
    uint8_t f_acc[6] = {0x01, 0x06, 0x62, 0x04, (uint8_t)(current_acc >> 8), (uint8_t)(current_acc & 0xFF)};
    memcpy(frame, f_acc, 6); append_crc(frame, 6); modbus_send_motor(frame, 8);
    DBG_PRINT("DBG: Frame3 sent -> 0x6204 (Acc)\r\n");

    // --- Frame 4: Write deceleration to 0x6205 (Pr9.05), unit: ms/1000rpm ---
    uint8_t f_dec[6] = {0x01, 0x06, 0x62, 0x05, (uint8_t)(current_dec >> 8), (uint8_t)(current_dec & 0xFF)};
    memcpy(frame, f_dec, 6); append_crc(frame, 6); modbus_send_motor(frame, 8);
    DBG_PRINT("DBG: Frame4 sent -> 0x6205 (Dec)\r\n");

    // --- Frame 5: Trigger PR Path 0 via PR Control Register 0x6002 = 0x0010 ---
    // Manual: "Write 0x1P (P=0-15) to run path P" — Path 0 = 0x10
    uint8_t f_go[6] = {0x01, 0x06, 0x60, 0x02, 0x00, 0x10};
    memcpy(frame, f_go, 6); append_crc(frame, 6); modbus_send_motor(frame, 8);
    DBG_PRINT("DBG: Frame5 sent -> 0x6002=0x0010 (TRIGGER Path 0)\r\n");
}

void Leadshine_Send_Stop(void) {
    uint8_t frame[8];

    // FLUSH the queue: Erase any pending Start commands so they don't fire after we Stop
    motor_tx_head = motor_tx_tail;

    // Write Quick Stop to PR Control Register 0x6002 = 0x0040
    // Manual section 5.3.3: "Write value 0x040 to 0x6002 = E-stop"
    uint8_t f_stop[6] = {0x01, 0x06, 0x60, 0x02, 0x00, 0x40};
    memcpy(frame, f_stop, 6); append_crc(frame, 6); 
    
    // BURST STOP: The Leadshine drive often ignores Modbus commands if it is currently 
    // busy calculating acceleration curves from a Start command received just milliseconds prior.
    // By spamming the Stop command 4 times (spanning 20ms), we guarantee the drive catches it.
    modbus_send_motor(frame, 8);
    modbus_send_motor(frame, 8);
    modbus_send_motor(frame, 8);
    modbus_send_motor(frame, 8);
    
    DBG_PRINT("DBG: STOP burst sent -> 0x6002=0x0040 (Quick Stop)\r\n");
}


// ---------------------------------------------------------
// ---------------------------------------------------------
// UART ERROR CALLBACK: Clears UART3 errors and restarts reception.
// At 256000 baud with Even parity, overrun/parity errors can occur.
// Without this, a single error silently kills HAL_UART_Receive_IT,
// freezing the sensor buffer permanently.
// ---------------------------------------------------------
void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART3) {
        // Clear all UART3 error flags
        __HAL_UART_CLEAR_OREFLAG(huart);
        __HAL_UART_CLEAR_NEFLAG(huart);
        __HAL_UART_CLEAR_FEFLAG(huart);
        __HAL_UART_CLEAR_PEFLAG(huart);
        sensor_state = 0; // Reset sensor state machine
        HAL_UART_Receive_IT(&huart3, &sensor_rx_byte, 1); // Restart reception
    }
}

// ---------------------------------------------------------
// HARDWARE INTERRUPT: Triggers every time a single byte arrives (IT mode)
// Note: USART1 RX is handled separately via DMA+Idle callback below.
// ---------------------------------------------------------
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)

{
    if (huart->Instance == USART2) {
        // Push incoming character to ring buffer
        uart2_rx_ring[uart2_ring_head] = uart2_rx_byte;
        uart2_ring_head = (uart2_ring_head + 1) % UART2_RING_SIZE;
        // Re-arm interrupt
        HAL_UART_Receive_IT(&huart2, &uart2_rx_byte, 1);
    }
    else if (huart->Instance == UART5) {
        // Eurotherm Modbus buffer
        eurotherm_rx_buffer[eurotherm_rx_index++] = eurotherm_rx_byte;
        if(eurotherm_rx_index >= 256) eurotherm_rx_index = 0; // Prevent overflow
        HAL_UART_Receive_IT(&huart5, &eurotherm_rx_byte, 1);
    }
    else if (huart->Instance == USART3) {
        // Micro-Epsilon Sensor Ring Buffer
        sensor_rx_buffer[sensor_rx_index++] = sensor_rx_byte;
        if(sensor_rx_index >= 256) sensor_rx_index = 0; // Prevent overflow
        HAL_UART_Receive_IT(&huart3, &sensor_rx_byte, 1);
    }
}

// ---------------------------------------------------------
// DMA + IDLE LINE CALLBACK: Called by HAL when USART1 DMA
// transfer completes or the line goes idle (end of Modbus frame).
// ---------------------------------------------------------
void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *huart, uint16_t Size)
{
    if (huart->Instance == USART1) {
        if (Size == 9) {
            // Verify Modbus CRC on the first 7 bytes; CRC is at bytes [7] (LSB) and [8] (MSB)
            uint16_t rx_crc  = ((uint16_t)enc_rx_buffer[8] << 8) | enc_rx_buffer[7];
            uint16_t cal_crc = modbus_crc(enc_rx_buffer, 7);

            if (rx_crc == cal_crc) {
                // Extract High Word (register 0x602C) and Low Word (register 0x602D)
                uint16_t hi = ((uint16_t)enc_rx_buffer[3] << 8) | enc_rx_buffer[4];
                uint16_t lo = ((uint16_t)enc_rx_buffer[5] << 8) | enc_rx_buffer[6];
                // Merge into signed 32-bit encoder position
                g_encoder_position = (int32_t)(((uint32_t)hi << 16) | lo);
                g_enc_data_ready   = 1;
            } else {
                // CRC mismatch — stale position retained, flag set for diagnostics
                g_enc_crc_fail = 1;
            }
        }
        // If Size == 8 it is likely the FC06 echo from a motor write — ignore.
        // Re-arm DMA listener for the next frame and release the bus.
        HAL_UARTEx_ReceiveToIdle_DMA(&huart1, enc_rx_buffer, ENC_RX_BUF_SIZE);
        encoder_bus_busy = 0;
    }
}


// ---------------------------------------------------------
// FOREGROUND TASKS
// ---------------------------------------------------------
void Process_Pi_Commands(void) {
    static char cmd_buf[64];
    static uint8_t cmd_idx = 0;

    // Process all available characters in the ring buffer
    while (uart2_ring_tail != uart2_ring_head) {
        char c = uart2_rx_ring[uart2_ring_tail];
        uart2_ring_tail = (uart2_ring_tail + 1) % UART2_RING_SIZE;

        if (c == '\n' || c == '\r') {
            cmd_buf[cmd_idx] = '\0'; // Null-terminate the command
            if (cmd_idx > 0) {
                // We have a complete command, process it immediately
                if (strncmp(cmd_buf, "Start", 5) == 0) {
                    pi_cmd_start    = true;
                    pi_cmd_stop     = false;
                    pi_cmd_pullback = false;
                    DBG_PRINT("DBG: CMD=Start -> pi_cmd_start set\r\n");
                }
                else if (strncmp(cmd_buf, "Stop", 4) == 0) {
                    pi_cmd_stop     = true;
                    pi_cmd_start    = false;
                    pi_cmd_pullback = false;
                    DBG_PRINT("DBG: CMD=Stop -> pi_cmd_stop set\r\n");
                }
                else if (strncmp(cmd_buf, "JogUp", 5) == 0) {
                    pi_cmd_start    = true;
                    pi_cmd_stop     = false;
                    pi_cmd_pullback = false;
                    motor_speed_setpoint = abs(motor_speed_setpoint); // CW direction
                    DBG_PRINT("DBG: CMD=JogUp -> pi_cmd_start set\r\n");
                }
                else if (strncmp(cmd_buf, "JogDown", 7) == 0) {
                    pi_cmd_start    = true;
                    pi_cmd_stop     = false;
                    pi_cmd_pullback = false;
                    motor_speed_setpoint = -abs(motor_speed_setpoint); // CCW direction
                    DBG_PRINT("DBG: CMD=JogDown -> pi_cmd_start set (reverse)\r\n");
                }
                else if (strncmp(cmd_buf, "Vel:", 4) == 0) {
                    int speed = atoi(&cmd_buf[4]);
                    if (speed != 0) {
                        motor_speed_setpoint = (int16_t)speed;
                        char dbg[48];
                        int len = snprintf(dbg, sizeof(dbg), "DBG: CMD=Vel -> setpoint=%d RPM\r\n", motor_speed_setpoint);
                        HAL_UART_Transmit(&huart2, (uint8_t*)dbg, len, 20);
                    } else {
                        DBG_PRINT("DBG: CMD=Vel -> IGNORED (speed=0)\r\n");
                    }
                }
                else if (strncmp(cmd_buf, "Pullback:", 9) == 0) {
                    int32_t counts = (int32_t)atoi(&cmd_buf[9]);
                    if (counts > 0) {
                        pullback_target_counts = counts;
                        pi_cmd_pullback        = true;
                        pi_cmd_start           = false;
                        pi_cmd_stop            = false;
                        char dbg[56];
                        int len = snprintf(dbg, sizeof(dbg), "DBG: CMD=Pullback -> counts=%ld\r\n", (long)counts);
                        HAL_UART_Transmit(&huart2, (uint8_t*)dbg, len, 20);
                    } else {
                        DBG_PRINT("DBG: CMD=Pullback -> IGNORED (counts<=0)\r\n");
                    }
                }
                else if (strncmp(cmd_buf, "PullSpeed:", 10) == 0) {
                    int spd = atoi(&cmd_buf[10]);
                    if (spd > 0 && spd <= 200) {
                        pullback_speed_rpm = (int16_t)spd;
                        char dbg[48];
                        int len = snprintf(dbg, sizeof(dbg), "DBG: CMD=PullSpeed -> %d RPM\r\n", spd);
                        HAL_UART_Transmit(&huart2, (uint8_t*)dbg, len, 20);
                    } else {
                        DBG_PRINT("DBG: CMD=PullSpeed -> IGNORED (out of range)\r\n");
                    }
                }
                else {
                    /* Unknown command */
                    char dbg[72];
                    int len = snprintf(dbg, sizeof(dbg), "DBG: CMD=UNKNOWN [%s]\r\n", cmd_buf);
                    HAL_UART_Transmit(&huart2, (uint8_t*)dbg, len, 20);
                }

                cmd_idx = 0; // Reset index for the next command
            }
        } else {
            // Append character to the local command buffer
            if (cmd_idx < sizeof(cmd_buf) - 1) {
                cmd_buf[cmd_idx++] = c;
            }
        }
    }
}

void Process_Motor(void) {
    char dbg[64];
    int  len;

    /* ── KILL SWITCH: absolute priority, cancels everything ──
     * NOTE: If no physical kill switch is wired, GPIOB Pin 5 will float and
     * randomly read GPIO_PIN_RESET, blocking all motor commands.
     * FIX (software): Enable the internal pull-up for GPIOB Pin 5 in
     * MX_GPIO_Init() by setting GPIO_PULLUP in the GPIO_InitStruct.
     * FIX (hardware): Wire a 10kΩ resistor from GPIOB Pin 5 to 3.3V.
     *
     * TEMPORARILY DISABLED FOR DEBUGGING:
     */
    /*
    if (HAL_GPIO_ReadPin(KILL_SWITCH_Port, KILL_SWITCH_Pin) == GPIO_PIN_RESET) {
        if (!kill_active) {
            kill_active = true;
            Leadshine_Send_Stop();
            DBG_PRINT("DBG: KILL SWITCH ACTIVE — motor STOPPED\r\n");
        }
        current_motor_state = MOTOR_IDLE;
        pi_cmd_start        = false;
        pi_cmd_stop         = false;
        pi_cmd_pullback     = false;
        return;
    } else {
        if (kill_active) {
            // Kill switch just released — report it
            DBG_PRINT("DBG: KILL SWITCH released\r\n");
        }
        kill_active = false;
    }
    */

    /* ── PULLBACK: takes priority over normal start/stop ── */
    if (pi_cmd_pullback) {
        pi_cmd_pullback         = false;
        pullback_start_position = g_encoder_position;
        Leadshine_Send_Start(pullback_speed_rpm);
        current_motor_state     = MOTOR_PULLBACK;
        len = snprintf(dbg, sizeof(dbg), "DBG: PULLBACK START spd=%d enc_start=%ld\r\n",
                       pullback_speed_rpm, (long)pullback_start_position);
        HAL_UART_Transmit(&huart2, (uint8_t*)dbg, len, 20);
        return;
    }

    /* ── MONITOR PULLBACK PROGRESS ── */
    if (current_motor_state == MOTOR_PULLBACK) {
        int32_t travelled = g_encoder_position - pullback_start_position;
        if (travelled >= pullback_target_counts) {
            Leadshine_Send_Stop();
            current_motor_state = MOTOR_IDLE;
            len = snprintf(dbg, sizeof(dbg), "DBG: PULLBACK DONE travelled=%ld\r\n", (long)travelled);
            HAL_UART_Transmit(&huart2, (uint8_t*)dbg, len, 20);
            const char *done_msg = "PULLBACK_DONE\r\n";
            HAL_UART_Transmit(&huart2, (uint8_t*)done_msg, 15, 20);
        }
        return;
    }

    /* ── NORMAL STOP ── */
    if (pi_cmd_stop) {
        if (current_motor_state != MOTOR_IDLE) {
            Leadshine_Send_Stop();
            current_motor_state = MOTOR_IDLE;
            DBG_PRINT("DBG: STOP frame sent — motor IDLE\r\n");
        } else {
            DBG_PRINT("DBG: STOP received but motor already IDLE\r\n");
        }
        pi_cmd_stop = false;
        return;
    }

    /* ── NORMAL START ──
     * BUG FIX: pi_cmd_start was never cleared, causing the condition below
     * to be re-evaluated every 5 ms. Now cleared immediately on entry so
     * Leadshine_Send_Start() fires exactly once per Start command. */
    if (pi_cmd_start) {
        pi_cmd_start = false;   /* <-- FIX: clear the flag immediately */
        if (current_motor_state != MOTOR_RUNNING || current_velocity != (int16_t)motor_speed_setpoint) {
            current_velocity    = (int16_t)motor_speed_setpoint;
            Leadshine_Send_Start(current_velocity);
            current_motor_state = MOTOR_RUNNING;
            len = snprintf(dbg, sizeof(dbg), "DBG: START frames sent — vel=%d RPM\r\n", current_velocity);
            HAL_UART_Transmit(&huart2, (uint8_t*)dbg, len, 20);
        } else {
            DBG_PRINT("DBG: START received but motor already at target speed\r\n");
        }
    }
}


void Process_Eurotherm(void) {
    uint32_t current_tick = HAL_GetTick();

    if (eurotherm_state == 0) {
        // Poll every 500ms
        if (current_tick - last_eurotherm_poll >= 500) {
            // Modbus Read Holding Registers: Slave 1, Func 3, Addr 1, 1 Register
            // FIX: Made static (fixes the stack bug) and using non-blocking IT transmit
            static uint8_t req[8] = {0x01, 0x03, 0x00, 0x01, 0x00, 0x01, 0, 0};
            uint16_t crc = modbus_crc(req, 6);
            req[6] = crc & 0xFF;
            req[7] = (crc >> 8) & 0xFF;
            eurotherm_rx_index = 0;
            HAL_UART_Transmit_IT(&huart5, req, 8); // Non-blocking transmit
            last_eurotherm_poll = current_tick;
            eurotherm_state = 1;
        }
    }
    else if (eurotherm_state == 1) {
        // Check for idle line to indicate end of response
        if (eurotherm_rx_index > 0 && eurotherm_rx_index == last_eurotherm_rx_index) {
            // Check SlaveID (0x01), Func (0x03), and ByteCount (0x02) to ignore TX echoes
            if (eurotherm_rx_index >= 7 && eurotherm_rx_buffer[0] == 0x01 && eurotherm_rx_buffer[1] == 0x03 && eurotherm_rx_buffer[2] == 0x02) {
                uint16_t received_crc = (eurotherm_rx_buffer[eurotherm_rx_index - 1] << 8) | eurotherm_rx_buffer[eurotherm_rx_index - 2];
                uint16_t calculated_crc = modbus_crc(eurotherm_rx_buffer, eurotherm_rx_index - 2);

                if (received_crc == calculated_crc) {
                    int16_t raw_temp = (eurotherm_rx_buffer[3] << 8) | eurotherm_rx_buffer[4];
                    eurotherm_temp = (float)raw_temp; // Match python script: 0 decimal places
                }
            }
            eurotherm_state = 0; // Go back to poll
        } else if (current_tick - last_eurotherm_poll >= 250) { // 250ms timeout (increased for 9600 baud)
            eurotherm_state = 0;
        }
    }
    last_eurotherm_rx_index = eurotherm_rx_index;
}

void Process_Sensor(void) {
    uint32_t tick = HAL_GetTick();
    switch (sensor_state) {
        case 0: { // Request
            if (tick - last_me_req_tick >= 50) { // 20Hz = 50ms period
                // FIX: Made static to avoid stack corruption.
                // Using non-blocking IT transmit as requested.
                static uint8_t req[] = {0x10, 0x7E, 0x01, 0x4C, 0xCB, 0x16};
                sensor_rx_index = 0; // Clear the buffer for a fresh response
                
                HAL_UART_Transmit_IT(&huart3, req, 6); // Non-blocking transmit
                
                last_me_req_tick = tick;
                sensor_state = 1;
            }
            break;
        }
        case 1: { // Wait response
            if (sensor_rx_index >= 17) {
                // Search for the start pattern 0x68 0x0B 0x0B 0x68 and stop byte 0x16
                for (int i = 0; i <= sensor_rx_index - 17; i++) {
                    if (sensor_rx_buffer[i] == 0x68 && sensor_rx_buffer[i+1] == 0x0B &&
                        sensor_rx_buffer[i+2] == 0x0B && sensor_rx_buffer[i+3] == 0x68 &&
                        sensor_rx_buffer[i+16] == 0x16) {

                        uint8_t sum = 0;
                        for (int j = 4; j <= 14; j++) {
                            sum += sensor_rx_buffer[i+j];
                        }
                        if (sum == sensor_rx_buffer[i+15]) {
                            // Valid checksum! Extract floats
                            memcpy(&unscaled_val, &sensor_rx_buffer[i+7], 4);
                            memcpy(&scaled_val, &sensor_rx_buffer[i+11], 4);

                            // Immediately compute tared displacement for telemetry
                            raw_displacement = scaled_val;
                            tared_displacement = scaled_val - me_tare_offset;
                        }
                        break; // Stop scanning once we find the packet
                    }
                }
                sensor_state = 0; // ready for next request
            } else if (tick - last_me_req_tick >= 45) { // Timeout
                sensor_state = 0;
            }
            break;
        }
    }
}

// ---------------------------------------------------------
// ENCODER POLLING — Non-blocking, 50 ms interval (20 Hz)
// Only fires when the USART1 bus is free (not mid motor command).
// ---------------------------------------------------------
void Process_Encoder(void)
{
    uint32_t tick = HAL_GetTick();

    // Poll every 50 ms, only if bus is idle
    if (!encoder_bus_busy && (tick - last_enc_poll >= 50)) {
        encoder_bus_busy = 1;       // Reserve the bus
        last_enc_poll    = tick;
        // Send the pre-built 8-byte FC03 read request to the motor controller
        HAL_UART_Transmit(&huart1, enc_request_frame, 8, 10);
        // DMA is already listening; response will trigger HAL_UARTEx_RxEventCallback
    }

    // Safety timeout: if no response arrives within 100 ms, release the bus
    // to prevent the encoder from locking out motor commands indefinitely.
    if (encoder_bus_busy && (tick - last_enc_poll >= 100)) {
        encoder_bus_busy = 0;
        // Re-arm DMA so it is ready for the next cycle
        HAL_UARTEx_ReceiveToIdle_DMA(&huart1, enc_rx_buffer, ENC_RX_BUF_SIZE);
    }
}
/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_DMA_Init();
  MX_USART2_UART_Init();
  MX_UART5_Init();
  MX_USART1_UART_Init();
  MX_USART3_UART_Init();
  MX_I2C2_Init();
  /* USER CODE BEGIN 2 */
  // Arm the non-blocking UART Receive Interrupts
  HAL_UART_Receive_IT(&huart2, &uart2_rx_byte, 1);    // Listen to Pi
  HAL_UART_Receive_IT(&huart3, &sensor_rx_byte, 1);   // Listen to MSC7xxx Sensor
  HAL_UART_Receive_IT(&huart5, &eurotherm_rx_byte, 1); // Listen to Eurotherm

  // Build the encoder Modbus request frame once (FC03: Slave 0x01, read 2 regs from 0x1014)
  // 0x1014 = encoder position high word, 0x1015 = encoder position low word (CS2RS Stepper Drive)
  {
    uint8_t base[6] = {0x01, 0x03, 0x10, 0x14, 0x00, 0x02};
    uint16_t crc = modbus_crc(base, 6);
    memcpy(enc_request_frame, base, 6);
    enc_request_frame[6] = (uint8_t)(crc & 0xFF);  // CRC LSB
    enc_request_frame[7] = (uint8_t)(crc >> 8);    // CRC MSB
  }

  // Start DMA listener on USART1 RX — passive, never blocks
  HAL_UARTEx_ReceiveToIdle_DMA(&huart1, enc_rx_buffer, ENC_RX_BUF_SIZE);
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
	  uint32_t current_tick = HAL_GetTick();

	  if (current_tick - last_motor_update >= 5) {
	      Process_Pi_Commands();
	      Process_Motor();
	      last_motor_update = current_tick;
	  }

	  Process_Eurotherm();
	  Process_Sensor();    // Internal timings (20 Hz)
	  Process_Encoder();   // Non-blocking encoder poll (20 Hz, bus-arbitrated)
	  Process_Motor_TX_Queue(); // Non-blocking motor Modbus queue

	  // Clear diagnostic flags in main loop (not in ISR to avoid race)
	  if (g_enc_crc_fail) {
	      g_enc_crc_fail = 0; // Position holds last valid value
	  }
	  if (g_enc_data_ready) {
	      g_enc_data_ready = 0; // Consumed — g_encoder_position already updated in ISR
	  }

	  if (current_tick - last_uart2_tx >= 50) { // 20 Hz telemetry to Raspberry Pi
	      char tx_buf[64];
	      // Format: Displacement (mm), Temperature (°C), Encoder Position (counts)
	      int len = snprintf(tx_buf, sizeof(tx_buf), "%.3f,%.1f,%ld\r\n",
	                         tared_displacement, eurotherm_temp, (long)g_encoder_position);
	      HAL_UART_Transmit(&huart2, (uint8_t*)tx_buf, len, 10);
	      last_uart2_tx = current_tick;
	  }
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Configure the main internal regulator output voltage
  */
  __HAL_RCC_PWR_CLK_ENABLE();
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE3);

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
  RCC_OscInitStruct.PLL.PLLM = 16;
  RCC_OscInitStruct.PLL.PLLN = 336;
  RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV4;
  RCC_OscInitStruct.PLL.PLLQ = 2;
  RCC_OscInitStruct.PLL.PLLR = 2;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief I2C2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_I2C2_Init(void)
{

  /* USER CODE BEGIN I2C2_Init 0 */

  /* USER CODE END I2C2_Init 0 */

  /* USER CODE BEGIN I2C2_Init 1 */

  /* USER CODE END I2C2_Init 1 */
  hi2c2.Instance = I2C2;
  hi2c2.Init.ClockSpeed = 100000;
  hi2c2.Init.DutyCycle = I2C_DUTYCYCLE_2;
  hi2c2.Init.OwnAddress1 = 0;
  hi2c2.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
  hi2c2.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
  hi2c2.Init.OwnAddress2 = 0;
  hi2c2.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
  hi2c2.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
  if (HAL_I2C_Init(&hi2c2) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN I2C2_Init 2 */

  /* USER CODE END I2C2_Init 2 */

}

/**
  * @brief UART5 Initialization Function
  * @param None
  * @retval None
  */
static void MX_UART5_Init(void)
{

  /* USER CODE BEGIN UART5_Init 0 */

  /* USER CODE END UART5_Init 0 */

  /* USER CODE BEGIN UART5_Init 1 */

  /* USER CODE END UART5_Init 1 */
  huart5.Instance = UART5;
  huart5.Init.BaudRate = 9600;
  huart5.Init.WordLength = UART_WORDLENGTH_8B;
  huart5.Init.StopBits = UART_STOPBITS_2;
  huart5.Init.Parity = UART_PARITY_NONE;
  huart5.Init.Mode = UART_MODE_TX_RX;
  huart5.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart5.Init.OverSampling = UART_OVERSAMPLING_16;
  if (HAL_UART_Init(&huart5) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN UART5_Init 2 */

  /* USER CODE END UART5_Init 2 */

}

/**
  * @brief USART1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART1_UART_Init(void)
{

  /* USER CODE BEGIN USART1_Init 0 */

  /* USER CODE END USART1_Init 0 */

  /* USER CODE BEGIN USART1_Init 1 */

  /* USER CODE END USART1_Init 1 */
  huart1.Instance = USART1;
  huart1.Init.BaudRate = 115200;
  huart1.Init.WordLength = UART_WORDLENGTH_8B;
  huart1.Init.StopBits = UART_STOPBITS_1;
  huart1.Init.Parity = UART_PARITY_NONE;
  huart1.Init.Mode = UART_MODE_TX_RX;
  huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart1.Init.OverSampling = UART_OVERSAMPLING_16;
  if (HAL_UART_Init(&huart1) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART1_Init 2 */

  /* USER CODE END USART1_Init 2 */

}

/**
  * @brief USART2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART2_UART_Init(void)
{

  /* USER CODE BEGIN USART2_Init 0 */

  /* USER CODE END USART2_Init 0 */

  /* USER CODE BEGIN USART2_Init 1 */

  /* USER CODE END USART2_Init 1 */
  huart2.Instance = USART2;
  huart2.Init.BaudRate = 115200;
  huart2.Init.WordLength = UART_WORDLENGTH_8B;
  huart2.Init.StopBits = UART_STOPBITS_1;
  huart2.Init.Parity = UART_PARITY_NONE;
  huart2.Init.Mode = UART_MODE_TX_RX;
  huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart2.Init.OverSampling = UART_OVERSAMPLING_16;
  if (HAL_UART_Init(&huart2) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART2_Init 2 */

  /* USER CODE END USART2_Init 2 */

}

/**
  * @brief USART3 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART3_UART_Init(void)
{

  /* USER CODE BEGIN USART3_Init 0 */

  /* USER CODE END USART3_Init 0 */

  /* USER CODE BEGIN USART3_Init 1 */

  /* USER CODE END USART3_Init 1 */
  huart3.Instance = USART3;
  huart3.Init.BaudRate = 256000;
  huart3.Init.WordLength = UART_WORDLENGTH_9B;
  huart3.Init.StopBits = UART_STOPBITS_1;
  huart3.Init.Parity = UART_PARITY_EVEN;
  huart3.Init.Mode = UART_MODE_TX_RX;
  huart3.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart3.Init.OverSampling = UART_OVERSAMPLING_16;
  if (HAL_UART_Init(&huart3) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART3_Init 2 */

  /* USER CODE END USART3_Init 2 */

}

/**
  * Enable DMA controller clock
  */
static void MX_DMA_Init(void)
{

  /* DMA controller clock enable */
  __HAL_RCC_DMA2_CLK_ENABLE();

  /* DMA interrupt init */
  /* DMA2_Stream2_IRQn interrupt configuration */
  HAL_NVIC_SetPriority(DMA2_Stream2_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(DMA2_Stream2_IRQn);

}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  /* USER CODE BEGIN MX_GPIO_Init_1 */

  /* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOH_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(LD2_GPIO_Port, LD2_Pin, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_4, GPIO_PIN_RESET);

  /*Configure GPIO pin : B1_Pin */
  GPIO_InitStruct.Pin = B1_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_IT_FALLING;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(B1_GPIO_Port, &GPIO_InitStruct);

  /*Configure GPIO pin : LD2_Pin */
  GPIO_InitStruct.Pin = LD2_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(LD2_GPIO_Port, &GPIO_InitStruct);

  /*Configure GPIO pin : PB4 */
  GPIO_InitStruct.Pin = GPIO_PIN_4;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

  /*Configure GPIO pin : PB5 */
  GPIO_InitStruct.Pin = GPIO_PIN_5;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

  /* USER CODE BEGIN MX_GPIO_Init_2 */

  /* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
