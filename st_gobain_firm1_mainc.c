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

/* USER CODE BEGIN PV */
/* ======================================================== */
/* 1. MODBUS MEMORY MAP (Variables shared with HMI)         */
/* ======================================================== */
// Coils (0x) - Boolean Commands from Kinco
volatile uint8_t coil_jog_up = 0;
volatile uint8_t coil_jog_down = 0;
volatile uint8_t coil_stop = 0;
volatile uint8_t coil_tare = 0;
volatile uint8_t coil_record = 0;

// Holding Registers (4x) - Numerical Data
volatile float raw_displacement = 0.0f;
volatile float tared_displacement = 0.0f;
volatile uint16_t motor_speed_setpoint = 100; // Default startup speed
volatile uint16_t target_record_timer = 0;
volatile uint16_t current_elapsed_time = 0;

/* ======================================================== */
/* 2. NON-BLOCKING TIMERS                                   */
/* ======================================================== */
uint32_t last_sensor_poll = 0;
uint32_t last_hmi_process = 0;
uint32_t last_motor_update = 0;

/* ======================================================== */
/* 3. UART RX BUFFERS (For Interrupts)                      */
/* ======================================================== */
uint8_t hmi_rx_byte;
uint8_t sensor_rx_byte;

// Simple ring buffer placeholders (We will expand these in Phase 2)
uint8_t eurotherm_rx_buffer[256];
uint16_t eurotherm_rx_index = 0;

uint8_t sensor_rx_buffer[256];
uint16_t sensor_rx_index = 0;

typedef enum {
    MOTOR_IDLE,
    MOTOR_JOGGING_UP,
    MOTOR_JOGGING_DOWN
} MotorState_t;

MotorState_t current_motor_state = MOTOR_IDLE;
int16_t current_velocity = 100;
uint16_t current_acc = 100; // Default Acceleration
uint16_t current_dec = 100; // Default Deceleration

// Hardware safety flag
bool kill_active = false;

// Sensor Variables
float tare_offset = 0.0f;
uint8_t sensor_state = 0; // 0 = Ready to TX Poll, 1 = Waiting for RX Response

// Define the expected number of bytes from the sensor response
// 17 bytes for the 'Get Measuring Value' long frame
#define SENSOR_EXPECTED_BYTES 17
// Eurotherm Variables
volatile float eurotherm_temp = 0.0f;
uint16_t last_eurotherm_rx_index = 0;
uint32_t last_eurotherm_poll = 0;
uint8_t eurotherm_state = 0;

#define KILL_SWITCH_Pin GPIO_PIN_5
#define KILL_SWITCH_Port GPIOB
/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_USART2_UART_Init(void);
static void MX_I2C2_Init(void);
static void MX_UART5_Init(void);
static void MX_USART1_UART_Init(void);
static void MX_USART3_UART_Init(void);
/* USER CODE BEGIN PFP */
void Process_Motor(void);
void Process_Sensor(void);
void Process_Eurotherm(void);
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

uint8_t hmi_tx_buffer[64];
uint16_t last_hmi_rx_index = 0;

// Union to easily convert a 32-bit float into two 16-bit Modbus registers
typedef union {
    float f;
    uint16_t regs[2];
} FloatConverter;

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

// Use blocking transmit for motor commands so back-to-back frames don't collide
void modbus_send_motor(uint8_t *frame, uint16_t len) {
  HAL_UART_Transmit(&huart1, frame, len, 100);
  HAL_Delay(5); // Modbus inter-frame gap: allow slave to process
}

// ---------------------------------------------------------
// MOTOR COMMAND WRAPPERS
// ---------------------------------------------------------

void Leadshine_Send_Start(int16_t vel) {
    uint8_t frame[8];
    // We use Slave ID 0x03 for the motor as per reference code
    uint8_t en[] = {0x03, 0x06, 0x04, 0x05, 0x00, 0x83}; // Enable
    uint8_t mode[] = {0x03, 0x06, 0x62, 0x00, 0x00, 0x02}; // Velocity Mode
    uint8_t vel_frame[] = {0x03, 0x06, 0x62, 0x03, ((uint16_t)vel >> 8), ((uint16_t)vel & 0xFF)};
    uint8_t acc[] = {0x03, 0x06, 0x62, 0x04, (current_acc >> 8), current_acc & 0xFF};
    uint8_t dec[] = {0x03, 0x06, 0x62, 0x05, (current_dec >> 8), current_dec & 0xFF};
    uint8_t start[] = {0x03, 0x06, 0x60, 0x02, 0x00, 0x10};

    memcpy(frame, en, 6); append_crc(frame, 6); modbus_send_motor(frame, 8);
    memcpy(frame, mode, 6); append_crc(frame, 6); modbus_send_motor(frame, 8);
    memcpy(frame, vel_frame, 6); append_crc(frame, 6); modbus_send_motor(frame, 8);
    memcpy(frame, acc, 6); append_crc(frame, 6); modbus_send_motor(frame, 8);
    memcpy(frame, dec, 6); append_crc(frame, 6); modbus_send_motor(frame, 8);
    memcpy(frame, start, 6); append_crc(frame, 6); modbus_send_motor(frame, 8);
}

void Leadshine_Send_Stop(void) {
    uint8_t frame[8];
    uint8_t stop[] = {0x03, 0x06, 0x60, 0x02, 0x00, 0x40};
    uint8_t dis[]  = {0x03, 0x06, 0x04, 0x05, 0x00, 0x03};

    memcpy(frame, stop, 6); append_crc(frame, 6); modbus_send_motor(frame, 8);
    memcpy(frame, dis, 6); append_crc(frame, 6); modbus_send_motor(frame, 8);
}


// ---------------------------------------------------------
// HARDWARE INTERRUPT: Triggers every time a single byte arrives
// ---------------------------------------------------------
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == UART5) {
        // 1. Save byte to Eurotherm buffer
        eurotherm_rx_buffer[eurotherm_rx_index++] = hmi_rx_byte;
        if(eurotherm_rx_index >= 256) eurotherm_rx_index = 0; // Prevent overflow

        // 2. Re-arm the interrupt for the next byte
        HAL_UART_Receive_IT(&huart5, &hmi_rx_byte, 1);
    }
    else if (huart->Instance == USART3) {
        // 1. Save byte to Sensor buffer
        sensor_rx_buffer[sensor_rx_index++] = sensor_rx_byte;
        if(sensor_rx_index >= 256) sensor_rx_index = 0; // Prevent overflow

        // 2. Re-arm the interrupt for the next byte
        HAL_UART_Receive_IT(&huart3, &sensor_rx_byte, 1);
    }
}

// ---------------------------------------------------------
// FOREGROUND TASKS
// ---------------------------------------------------------
void Process_Motor(void) {
	// ==============================================================
	    // 1. HARDWARE KILL SWITCH (Absolute Priority)
	    // ==============================================================
	    if (HAL_GPIO_ReadPin(KILL_SWITCH_Port, KILL_SWITCH_Pin) == GPIO_PIN_RESET) {
	        if (!kill_active) {
	            kill_active = true;
	            Leadshine_Send_Stop();
	            // Optional: send disable command 5ms later using a state machine
	        }
	        // Force the software state to idle and clear any HMI requests
	        current_motor_state = MOTOR_IDLE;
	        coil_jog_up = 0;
	        coil_jog_down = 0;
	        coil_stop = 0;
	        return; // CRITICAL: Exit immediately. No other motor commands can run.
	    } else {
	        kill_active = false;
	    }

	    // ==============================================================
	    // 2. SOFTWARE STOP (From Kinco HMI or double-button press)
	    // ==============================================================
	    if (coil_stop == 1 || (coil_jog_up == 1 && coil_jog_down == 1)) {
	        if (current_motor_state != MOTOR_IDLE) {
	            Leadshine_Send_Stop();
	            current_motor_state = MOTOR_IDLE;
	        }
	        // We DO NOT clear coil_stop here!
	        // We let the Kinco HMI clear it when the user lets go of the button.
	        // As long as coil_stop is 1, this returns immediately, completely
	        // blocking the JOG commands below.
	        return;
	    }

	    // ==============================================================
	    // 3. JOG UP (Positive Velocity)
	    // ==============================================================
	    if (coil_jog_up == 1) {
	        // If we are starting from idle, or the user changed speed mid-jog
	        if (current_motor_state != MOTOR_JOGGING_UP || current_velocity != motor_speed_setpoint) {

	            current_velocity = motor_speed_setpoint; // Get speed from HMI register
	            Leadshine_Send_Start(current_velocity);

	            current_motor_state = MOTOR_JOGGING_UP;
	        }
	    }

	    // ==============================================================
	    // 4. JOG DOWN (Negative Velocity)
	    // ==============================================================
	    else if (coil_jog_down == 1) {
	        if (current_motor_state != MOTOR_JOGGING_DOWN || current_velocity != (motor_speed_setpoint * -1)) {

	            current_velocity = (motor_speed_setpoint * -1); // Make speed negative
	            Leadshine_Send_Start(current_velocity);

	            current_motor_state = MOTOR_JOGGING_DOWN;
	        }
	    }

	    // ==============================================================
	    // 5. RELEASE (Stop when button is let go)
	    // ==============================================================
	    else {
	        if (current_motor_state != MOTOR_IDLE) {
	            Leadshine_Send_Stop();
	            current_motor_state = MOTOR_IDLE;
	        }
	    }

}

void Process_Sensor(void) {
	// ==============================================================
	    // 1. TARE COMMAND OVERRIDE
	    // ==============================================================
	    // If the operator pressed 'TARE' on the HMI, snapshot the current raw value
	    if (coil_tare == 1) {
	        tare_offset = raw_displacement;
	        coil_tare = 0; // Clear the flag so it only triggers once
	    }

	    // ==============================================================
	    // 2. STATE 1: PARSE THE INCOMING DATA (From previous cycle)
	    // ==============================================================
	    if (sensor_state == 1) {
	        // Check if the hardware interrupt has filled the buffer with enough bytes
	        if (sensor_rx_index >= SENSOR_EXPECTED_BYTES) {

	            // Validate packet header (Start Byte 0x68, Length 0x0B repeated, Start Byte 0x68)
	            // and Stop Byte (0x16)
	            if (sensor_rx_buffer[0] == 0x68 && sensor_rx_buffer[1] == 0x0B && 
	                sensor_rx_buffer[2] == 0x0B && sensor_rx_buffer[3] == 0x68 && 
	                sensor_rx_buffer[16] == 0x16) {
	                
	                // Validate Checksum (Sum without arithmetic overflow mod 256)
	                // The checksum is the sum of DA(4), SA(5), FC(6), Data(7 to 14) -> Bytes 4 to 14
	                uint32_t checksum_sum = 0;
	                for (int i = 4; i <= 14; i++) {
	                    checksum_sum += sensor_rx_buffer[i];
	                }
	                uint8_t calculated_checksum = (uint8_t)(checksum_sum % 256);

	                if (sensor_rx_buffer[15] == calculated_checksum) {
	                    // Protocol matches! Extract 4-byte float (Little Endian) from bytes 8, 9, 10, 11
	                    uint32_t raw_uint = ((uint32_t)sensor_rx_buffer[11] << 24) | 
	                                        ((uint32_t)sensor_rx_buffer[10] << 16) | 
	                                        ((uint32_t)sensor_rx_buffer[9] << 8) | 
	                                        (uint32_t)sensor_rx_buffer[8];
	                    
	                    float parsed_val;
	                    memcpy(&parsed_val, &raw_uint, sizeof(float));
	                    
	                    raw_displacement = parsed_val;

	                    // Calculate the zeroed value for the HMI graph
	                    tared_displacement = raw_displacement - tare_offset;
	                }
	            }

	            sensor_state = 0; // Success. Reset state to poll again.
	        }
	        else {
	            // Timeout Recovery: If 10ms passed and the sensor didn't send enough bytes,
	            // the wire might be loose. Reset state to force a new poll request.
	            sensor_rx_index = 0;
	            sensor_state = 0;
	        }
	    }

	    // ==============================================================
	    // 3. STATE 0: SEND THE POLL REQUEST
	    // ==============================================================
	    if (sensor_state == 0) {
	        // Get Measuring Value Command (Page 101)
	        uint8_t poll_cmd[] = {0x10, 0x7E, 0x01, 0x4C, 0xCB, 0x16};

	        sensor_rx_index = 0; // Clear the old data from the buffer

	        // Transmit the request non-blocking
	        HAL_UART_Transmit_IT(&huart3, poll_cmd, sizeof(poll_cmd));

	        sensor_state = 1; // Tell the machine to look for the answer next cycle
	    }
}

void Process_Eurotherm(void) {
    uint32_t current_tick = HAL_GetTick();

    if (eurotherm_state == 0) {
        // Poll every 500ms
        if (current_tick - last_eurotherm_poll >= 500) {
            // Modbus Read Holding Registers: Slave 1, Func 3, Addr 1, 1 Register
            uint8_t req[8] = {0x01, 0x03, 0x00, 0x01, 0x00, 0x01, 0, 0};
            append_crc(req, 6);
            eurotherm_rx_index = 0;
            HAL_UART_Transmit_IT(&huart5, req, 8);
            last_eurotherm_poll = current_tick;
            eurotherm_state = 1;
        }
    }
    else if (eurotherm_state == 1) {
        // Check for idle line to indicate end of response
        if (eurotherm_rx_index > 0 && eurotherm_rx_index == last_eurotherm_rx_index) {
            if (eurotherm_rx_index >= 7 && eurotherm_rx_buffer[0] == 0x01 && eurotherm_rx_buffer[1] == 0x03) {
                uint16_t received_crc = (eurotherm_rx_buffer[eurotherm_rx_index - 1] << 8) | eurotherm_rx_buffer[eurotherm_rx_index - 2];
                uint16_t calculated_crc = modbus_crc(eurotherm_rx_buffer, eurotherm_rx_index - 2);

                if (received_crc == calculated_crc) {
                    int16_t raw_temp = (eurotherm_rx_buffer[3] << 8) | eurotherm_rx_buffer[4];
                    eurotherm_temp = (float)raw_temp / 10.0f; // Assume 1 decimal place
                }
            }
            eurotherm_state = 0; // Go back to poll
        } else if (current_tick - last_eurotherm_poll >= 100) { // 100ms timeout
            eurotherm_state = 0;
        }
    }
    last_eurotherm_rx_index = eurotherm_rx_index;
}

#if 0
void Process_HMI(void) {
	    // This signifies the Kinco screen has finished sending its Modbus frame.
	    if (hmi_rx_index > 0 && hmi_rx_index == last_hmi_rx_index) {

	        // 2. Validate Minimum Frame Size and Slave ID (Assume STM32 is ID 1)
	        if (hmi_rx_index >= 8 && hmi_rx_buffer[0] == 0x01) {

	            // 3. Validate CRC
	            uint16_t received_crc = (hmi_rx_buffer[hmi_rx_index - 1] << 8) | hmi_rx_buffer[hmi_rx_index - 2];
	            uint16_t calculated_crc = modbus_crc(hmi_rx_buffer, hmi_rx_index - 2);

	            if (received_crc == calculated_crc) {
	                uint8_t function_code = hmi_rx_buffer[1];
	                uint16_t start_addr = (hmi_rx_buffer[2] << 8) | hmi_rx_buffer[3];
	                uint16_t tx_len = 0;

	                // ==============================================================
	                // FUNCTION 01: HMI Reads Coils
	                // ==============================================================
	                if (function_code == 0x01) {
	                    uint16_t num_coils = (hmi_rx_buffer[4] << 8) | hmi_rx_buffer[5];
	                    uint8_t byte_count = (num_coils + 7) / 8; // Round up to nearest byte

	                    hmi_tx_buffer[0] = 0x01; // Slave ID
	                    hmi_tx_buffer[1] = 0x01; // Function Code
	                    hmi_tx_buffer[2] = byte_count; // Byte Count
	                    tx_len = 3;

	                    for (int b = 0; b < byte_count; b++) {
	                        uint8_t coil_byte = 0;
	                        for (int bit = 0; bit < 8; bit++) {
	                            uint16_t current_addr = start_addr + (b * 8) + bit;
	                            uint8_t state = 0;

	                            if (current_addr == 0x0000) state = coil_jog_up;
	                            else if (current_addr == 0x0001) state = coil_jog_down;
	                            else if (current_addr == 0x0002) state = coil_stop;
	                            else if (current_addr == 0x0003) state = coil_tare;
	                            else if (current_addr == 0x0004) state = coil_record;

	                            if (state) {
	                                coil_byte |= (1 << bit);
	                            }
	                        }
	                        hmi_tx_buffer[tx_len++] = coil_byte;
	                    }

	                    // Append CRC
	                    uint16_t tx_crc = modbus_crc(hmi_tx_buffer, tx_len);
	                    hmi_tx_buffer[tx_len++] = tx_crc & 0xFF;        // CRC Low Byte
	                    hmi_tx_buffer[tx_len++] = (tx_crc >> 8) & 0xFF; // CRC High Byte
	                }

	                // ==============================================================
	                // FUNCTION 05: HMI Writes to a Coil (Buttons Pressed)
	                // ==============================================================
	                else if (function_code == 0x05) {
	                    uint16_t coil_val = (hmi_rx_buffer[4] << 8) | hmi_rx_buffer[5];
	                    uint8_t state = (coil_val == 0xFF00) ? 1 : 0; // 0xFF00 means ON in Modbus

	                    switch(start_addr) {
	                        case 0x0000: coil_jog_up = state; break;
	                        case 0x0001: coil_jog_down = state; break;
	                        case 0x0002: coil_stop = state; break;
	                        case 0x0003: coil_tare = state; break;
	                        case 0x0004: coil_record = state; break;
	                    }

	                    // For FC05, the standard response is simply echoing the exact request back
	                    memcpy(hmi_tx_buffer, hmi_rx_buffer, hmi_rx_index);
	                    tx_len = hmi_rx_index;
	                }

	                // ==============================================================
	                // FUNCTION 06: HMI Writes to a Single Register (Speed Setpoint)
	                // ==============================================================
	                else if (function_code == 0x06) {
	                    uint16_t reg_val = (hmi_rx_buffer[4] << 8) | hmi_rx_buffer[5];

	                    if (start_addr == 0x0004) { // Address for Speed
	                        motor_speed_setpoint = reg_val;
	                    }

	                    // Echo response
	                    memcpy(hmi_tx_buffer, hmi_rx_buffer, hmi_rx_index);
	                    tx_len = hmi_rx_index;
	                }

	                // ==============================================================
	                // FUNCTION 03: HMI Reads Holding Registers (Displacement & Speed)
	                // ==============================================================
	                else if (function_code == 0x03) {
	                    uint16_t num_regs = (hmi_rx_buffer[4] << 8) | hmi_rx_buffer[5];

	                    hmi_tx_buffer[0] = 0x01; // Slave ID
	                    hmi_tx_buffer[1] = 0x03; // Function Code
	                    hmi_tx_buffer[2] = num_regs * 2; // Byte Count
	                    tx_len = 3;

	                    FloatConverter raw_conv, tare_conv;
	                    raw_conv.f = raw_displacement;
	                    tare_conv.f = tared_displacement;

	                    // Fill the requested registers into the response buffer
	                    for (int i = 0; i < num_regs; i++) {
	                        uint16_t current_addr = start_addr + i;
	                        uint16_t data = 0;

	                        if (current_addr == 0x0000) data = raw_conv.regs[0]; // Raw Low Word
	                        else if (current_addr == 0x0001) data = raw_conv.regs[1]; // Raw High Word
	                        else if (current_addr == 0x0002) data = tare_conv.regs[0]; // Tare Low Word
	                        else if (current_addr == 0x0003) data = tare_conv.regs[1]; // Tare High Word
	                        else if (current_addr == 0x0004) data = motor_speed_setpoint;

	                        // Modbus requires High Byte first, then Low Byte
	                        hmi_tx_buffer[tx_len++] = (data >> 8) & 0xFF;
	                        hmi_tx_buffer[tx_len++] = data & 0xFF;
	                    }

	                    // Append CRC to response
	                    uint16_t tx_crc = modbus_crc(hmi_tx_buffer, tx_len);
	                    hmi_tx_buffer[tx_len++] = tx_crc & 0xFF;        // CRC Low Byte
	                    hmi_tx_buffer[tx_len++] = (tx_crc >> 8) & 0xFF; // CRC High Byte
	                }

	                // Transmit the compiled response back to the Kinco HMI
	                if (tx_len > 0) {
	                    // RS485 TURNAROUND DELAY:
	                    // The STM32 might be replying too fast! We must give the Kinco HMI a few
	                    // milliseconds to release the RS485 bus and switch its chip back into
	                    // 'Receive' mode before we blast the response back.
	                    HAL_Delay(5);
	                    HAL_UART_Transmit_IT(&huart5, hmi_tx_buffer, tx_len);
	                }
	            }
	        }
	        // Frame processed or invalid, reset the buffer index to catch the next frame
	        hmi_rx_index = 0;
	    }

	    // Update the tracker for idle line detection
	    last_hmi_rx_index = hmi_rx_index;
}
#endif



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
  MX_USART2_UART_Init();
  MX_I2C2_Init();
  MX_UART5_Init();
  MX_USART1_UART_Init();
  MX_USART3_UART_Init();
  /* USER CODE BEGIN 2 */
  // Arm the non-blocking UART Receive Interrupts
  HAL_UART_Receive_IT(&huart5, &hmi_rx_byte, 1);    // Listen to Kinco HMI
  HAL_UART_Receive_IT(&huart3, &sensor_rx_byte, 1); // Listen to MSC7xxx Sensor

  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
	  uint32_t current_tick = HAL_GetTick();

	        // TASK 1: Motor Control Loop (Highest Frequency - Runs every 5ms / 200Hz)
	        if (current_tick - last_motor_update >= 5) {
	            Process_Motor();
	            last_motor_update = current_tick;
	        }

	        // TASK 2: Sensor Polling Loop (Runs every 10ms / 100Hz)
	        if (current_tick - last_sensor_poll >= 10) {
	            Process_Sensor();
	            last_sensor_poll = current_tick;
	        }

	        // TASK 3: Eurotherm Processing Loop (Runs every 10ms)
	        if (current_tick - last_hmi_process >= 10) {
	            Process_Eurotherm();
	            last_hmi_process = current_tick;
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
  huart5.Init.StopBits = UART_STOPBITS_1;
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
  huart1.Init.StopBits = UART_STOPBITS_2;
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
  huart3.Init.BaudRate = 115200;
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

  /*Configure GPIO pin : PB5 (Hardware Kill Switch) */
  GPIO_InitStruct.Pin = GPIO_PIN_5;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_PULLUP; // Changed from NOPULL to PULLUP
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
