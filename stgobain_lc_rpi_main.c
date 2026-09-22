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
#include <string.h>
#include <stdio.h>
#include <math.h>
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
IWDG_HandleTypeDef hiwdg;
// --- DFRobot ADC Variables ---
static float ch1_val = 0.0f;
static float ch2_val = 0.0f;
static uint32_t last_adc_tick = 0;
static uint8_t current_channel = 1;
static uint8_t adc_state = 0;

// --- Micro-Epsilon Variables ---
static float scaled_val = 0.0f;
static float unscaled_val = 0.0f;
static float me_tare_offset = -6.202f; // Tare baseline for fully relaxed position
static uint32_t last_me_req_tick = 0;
static uint8_t me_rx_buffer[256];
static uint16_t me_rx_index = 0;
static uint8_t me_rx_byte;
static uint8_t me_state = 0;

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
static void MX_IWDG_Init(void);
void DFRobot_ADC_Init(I2C_HandleTypeDef *hi2c);
void DFRobot_ADC_Process(void);
float DFRobot_ADC_GetChannelValue(uint8_t channel);

void MicroEpsilon_Init(UART_HandleTypeDef *huart);
void MicroEpsilon_Process(void);
float MicroEpsilon_GetScaledValue(void);
float MicroEpsilon_GetUnscaledValue(void);

void UART2_SendNonBlocking(const char *str);
void I2C2_Bus_Recovery(void);
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */
void I2C2_Bus_Recovery(void) {
    // 1. DeInit I2C
    HAL_I2C_DeInit(&hi2c2);

    // 2. Configure PB10 (SCL) and PB3 (SDA) as standard GPIO outputs
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin = GPIO_PIN_10 | GPIO_PIN_3;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_OD;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

    // 3. Set SDA High, then clock SCL 9 times to free any stuck slave
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_3, GPIO_PIN_SET);
    HAL_Delay(1);
    for (int i = 0; i < 9; i++) {
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_10, GPIO_PIN_SET);
        HAL_Delay(1);
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_10, GPIO_PIN_RESET);
        HAL_Delay(1);
    }

    // Stop condition: SCL high, then SDA high
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_10, GPIO_PIN_SET);
    HAL_Delay(1);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_3, GPIO_PIN_SET);
    HAL_Delay(1);

    // 4. Re-Initialize I2C peripheral
    MX_I2C2_Init();
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
  MX_USART2_UART_Init();
  MX_I2C2_Init();
  MX_UART5_Init();
  MX_USART1_UART_Init();
  MX_USART3_UART_Init();
  /* USER CODE BEGIN 2 */
  MX_IWDG_Init();
  DFRobot_ADC_Init(&hi2c2);
  MicroEpsilon_Init(&huart3);

  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  static uint32_t last_uart_tick = 0;
  while (1)
  {
    HAL_IWDG_Refresh(&hiwdg);
    DFRobot_ADC_Process();
    MicroEpsilon_Process();

    uint32_t tick = HAL_GetTick();
    if (tick - last_uart_tick >= 50) { // Send every 50ms (20Hz)
      last_uart_tick = tick;

      float raw_disp = MicroEpsilon_GetScaledValue();
      float load_ch1 = DFRobot_ADC_GetChannelValue(1);

      uint8_t status = 0;
      if (isnan(raw_disp) || isinf(raw_disp)) {
          raw_disp = 0.0f;
          status |= 0x01; // Sensor 1 error
      }
      if (isnan(load_ch1) || isinf(load_ch1)) {
          load_ch1 = 0.0f;
          status |= 0x02; // Sensor 2 error
      }
      // If MicroEpsilon hasn't responded in 100ms
      if (tick - last_me_req_tick > 100) {
          status |= 0x04;
      }

      char tx_msg[64];
      // Format as CSV: $load,displacement,status\r\n
      int len = snprintf(tx_msg, sizeof(tx_msg), "$%.2f,%.3f,%d\r\n", load_ch1, raw_disp, status);
      if (len > 0 && len < sizeof(tx_msg)) {
        UART2_SendNonBlocking(tx_msg);
      }
    }
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
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
  huart5.Init.BaudRate = 115200;
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

  /* USER CODE BEGIN MX_GPIO_Init_2 */

  /* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */
static void MX_IWDG_Init(void)
{
  hiwdg.Instance = IWDG;
  hiwdg.Init.Prescaler = IWDG_PRESCALER_64;
  hiwdg.Init.Reload = 4095; // Approx 8.19 seconds timeout at 32kHz LSI
  if (HAL_IWDG_Init(&hiwdg) != HAL_OK)
  {
    Error_Handler();
  }
}

void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
  if (huart->Instance == USART3) {
    // MicroEpsilon UART Error
    __HAL_UART_CLEAR_OREFLAG(huart);
    __HAL_UART_CLEAR_NEFLAG(huart);
    __HAL_UART_CLEAR_FEFLAG(huart);
    __HAL_UART_CLEAR_PEFLAG(huart);
    me_state = 0; // Reset state machine
    HAL_UART_Receive_IT(&huart3, &me_rx_byte, 1); // Restart reception
  }
}

// ============================================================================
// DFRobot ADC Implementation
// ============================================================================
#define ADC_I2C_ADDR (0x4B << 1) // Using newly found address 0x4B
#define CHANNEL_SELECT_ADDRESS  0x20
#define CHANNEL_DATA_ADDRESS  0x31

static I2C_HandleTypeDef *adc_i2c;

void DFRobot_ADC_Init(I2C_HandleTypeDef *hi2c) {
    adc_i2c = hi2c;
    adc_state = 0;
    current_channel = 1;
}

void DFRobot_ADC_Process(void) {
    static uint8_t adc_err_cnt = 0;
    uint32_t tick = HAL_GetTick();

    switch (adc_state) {
        case 0: { // Start request
            // Use Mem_Write to correctly address the register
            if (HAL_I2C_Mem_Write(adc_i2c, ADC_I2C_ADDR, CHANNEL_SELECT_ADDRESS, I2C_MEMADD_SIZE_8BIT, &current_channel, 1, 100) != HAL_OK) {
                adc_err_cnt++;
            } else {
                adc_err_cnt = 0; // Reset counter on success
            }

            if (adc_err_cnt >= 3) {
                I2C2_Bus_Recovery();
                adc_err_cnt = 0;
            }

            last_adc_tick = tick;
            adc_state = 1;
            break;
        }
        case 1: { // Wait for conversion
            if (tick - last_adc_tick >= 60) { // 60ms wait without blocking main loop
                uint8_t rxData[3] = {0};

                // Use Mem_Read for robust register reading
                if (HAL_I2C_Mem_Read(adc_i2c, ADC_I2C_ADDR, CHANNEL_DATA_ADDRESS, I2C_MEMADD_SIZE_8BIT, rxData, 3, 100) == HAL_OK) {
                    adc_err_cnt = 0; // Reset counter on success

                    uint32_t ad_value = ((uint32_t)rxData[0] << 16) | ((uint32_t)rxData[1] << 8) | rxData[2];

                    float voltage_mv = (float)ad_value / 100.0f;
                    float voltage_v = voltage_mv / 1000.0f;

                    if (voltage_v < 0.0f) voltage_v = 0.0f;

                    // Convert 0-10V directly to 0-2943 Newtons
                    float weight_kg = (voltage_v / 10.0f) * 2943.0f;

                    if (current_channel == 1) {
                        static float ch1_hist[3] = {0.0f, 0.0f, 0.0f};
                        static uint8_t ch1_idx = 0;
                        static uint8_t ch1_count = 0;

                        ch1_hist[ch1_idx] = weight_kg;
                        ch1_idx = (ch1_idx + 1) % 3;
                        if (ch1_count < 3) ch1_count++;
                        
                        if (ch1_count == 3) {
                            float sorted[3] = {ch1_hist[0], ch1_hist[1], ch1_hist[2]};
                            if (sorted[0] > sorted[1]) { float t = sorted[0]; sorted[0] = sorted[1]; sorted[1] = t; }
                            if (sorted[1] > sorted[2]) { float t = sorted[1]; sorted[1] = sorted[2]; sorted[2] = t; }
                            if (sorted[0] > sorted[1]) { float t = sorted[0]; sorted[0] = sorted[1]; sorted[1] = t; }
                            ch1_val = sorted[1];
                        } else {
                            ch1_val = weight_kg; // Bypass filter until buffer fills
                        }
                    }
                    else {
                        ch2_val = weight_kg;
                    }
                } else {
                    adc_err_cnt++;
                    if (adc_err_cnt >= 3) {
                        I2C2_Bus_Recovery();
                        adc_err_cnt = 0;
                    }
                }

                current_channel = (current_channel == 1) ? 2 : 1;
                adc_state = 0; // Ready for next request
            }
            break;
        }
    }
}

float DFRobot_ADC_GetChannelValue(uint8_t channel) {
    if (channel == 1) return ch1_val;
    if (channel == 2) return ch2_val;
    return 0.0f;
}

// ============================================================================
// Micro-Epsilon Sensor Implementation
// ============================================================================
static UART_HandleTypeDef *me_uart;

void MicroEpsilon_Init(UART_HandleTypeDef *huart) {
    me_uart = huart;
    me_state = 0;
    // Start background 1-byte ring buffer reception
    HAL_UART_Receive_IT(me_uart, &me_rx_byte, 1);
}

void MicroEpsilon_Process(void) {
    uint32_t tick = HAL_GetTick();
    switch (me_state) {
        case 0: { // Request
            if (tick - last_me_req_tick >= 50) { // 20Hz = 50ms period
                uint8_t req[] = {0x10, 0x7E, 0x01, 0x4C, 0xCB, 0x16};
                me_rx_index = 0; // Clear the buffer for a fresh response
                HAL_UART_Transmit_IT(me_uart, req, 6);
                last_me_req_tick = tick;
                me_state = 1;
            }
            break;
        }
        case 1: { // Wait response
            if (me_rx_index >= 17) {
                // Search for the start pattern 0x68 0x0B 0x0B 0x68 and stop byte 0x16
                // This protects against RS485 TX echo or dropped noise bytes
                for (int i = 0; i <= me_rx_index - 17; i++) {
                    if (me_rx_buffer[i] == 0x68 && me_rx_buffer[i+1] == 0x0B && 
                        me_rx_buffer[i+2] == 0x0B && me_rx_buffer[i+3] == 0x68 && 
                        me_rx_buffer[i+16] == 0x16) {
                        
                        uint8_t sum = 0;
                        for (int j = 4; j <= 14; j++) {
                            sum += me_rx_buffer[i+j];
                        }
                        if (sum == me_rx_buffer[i+15]) {
                            // Valid checksum! Extract floats
                            memcpy(&unscaled_val, &me_rx_buffer[i+7], 4);
                            memcpy(&scaled_val, &me_rx_buffer[i+11], 4);
                        }
                        break; // Stop scanning once we find the packet
                    }
                }
                me_state = 0; // ready for next request
            } else if (tick - last_me_req_tick >= 45) { // Timeout
                me_state = 0;
            }
            break;
        }
    }
}

// ---------------------------------------------------------
// HARDWARE INTERRUPT: Triggers every time a single byte arrives
// ---------------------------------------------------------
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART3) {
        me_rx_buffer[me_rx_index++] = me_rx_byte;
        if (me_rx_index >= 256) me_rx_index = 0; // Prevent overflow
        HAL_UART_Receive_IT(&huart3, &me_rx_byte, 1);
    }
}

float MicroEpsilon_GetScaledValue(void) {
    // Subtract the fully relaxed baseline to shift 0mm
    return scaled_val - me_tare_offset;
}

float MicroEpsilon_GetUnscaledValue(void) {
    return unscaled_val;
}

// ============================================================================
// Non-blocking UART2 transmission
// ============================================================================
void UART2_SendNonBlocking(const char *str) {
    static char tx_buf[64];
    // Check if UART is ready to transmit new data (not busy)
    if (huart2.gState == HAL_UART_STATE_READY) {
        strncpy(tx_buf, str, sizeof(tx_buf) - 1);
        tx_buf[sizeof(tx_buf) - 1] = '\0';
        HAL_UART_Transmit_IT(&huart2, (uint8_t*)tx_buf, strlen(tx_buf));
    }
}
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
