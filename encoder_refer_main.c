/* USER CODE BEGIN Header */
/**
 ******************************************************************************
 * @file           : main.c
 * @brief          : Main program body
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 STMicroelectronics.
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
#include <stdio.h>
#include <string.h>

/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
#define MODBUS_RX_BUFFER_SIZE 16
/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
UART_HandleTypeDef huart1;
UART_HandleTypeDef huart2;
DMA_HandleTypeDef hdma_usart1_rx;

/* USER CODE BEGIN PV */
uint8_t enc_request_frame[8];
uint8_t modbus_rx_buffer[MODBUS_RX_BUFFER_SIZE];

// New buffer to safely copy data from the interrupt
uint8_t g_debug_rx_buffer[MODBUS_RX_BUFFER_SIZE];

// Volatile shared data & flags
volatile int32_t g_encoder_position = 0;
volatile uint8_t g_new_data_ready = 0;
volatile uint8_t g_callback_received = 0; // NEW: Flag to signal ANY callback
volatile uint16_t g_callback_size = 0; // NEW: Variable to store the packet size
volatile uint8_t g_crc_failed = 0;     // NEW: Flag to signal a bad CRC

// Debug print buffer
char g_usart2_buffer[100];
/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_DMA_Init(void);
static void MX_USART2_UART_Init(void);
static void MX_USART1_UART_Init(void);
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

// 1. Calculate the CRC for the first 6 bytes
uint16_t crc;

// DMA buffer for receiving the response (9 bytes expected)
static uint16_t crc16(const uint8_t *data, uint16_t length) {
  uint16_t crc = 0xFFFF;
  for (uint16_t i = 0; i < length; i++) {
    crc ^= (uint16_t)data[i];
    for (int j = 8; j != 0; j--) {
      if ((crc & 0x0001) != 0) {
        crc >>= 1;
        crc ^= 0xA001;
      } else {
        crc >>= 1;
      }
    }
  }
  // Return the CRC (e.g., 0x7E04)
  return crc;
}

/**
 * @brief  UART Receive Event Callback (called by HAL on DMA complete or Idle
 * Line).
 * @param  huart: Pointer to a UART_HandleTypeDef.
 * @param  Size: The number of bytes received.
 */
void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *huart, uint16_t Size) {
  if (huart->Instance == USART1) {
    // 1. Copy the data to our safe buffer and set flags
    // We do this *no matter what* for debugging
    memcpy(g_debug_rx_buffer, modbus_rx_buffer, Size);
    g_callback_size = Size;
    g_callback_received = 1; // Tell the main loop we got *something*

    // 2. Check for 8-byte echo
    if (Size == 8 && modbus_rx_buffer[0] == 0x10 &&
        modbus_rx_buffer[1] == 0x03) {
      // It's an echo, do nothing else.

    }
    // 3. Check for 9-byte valid response
    else if (Size == 9) {
      uint16_t received_crc =
          (modbus_rx_buffer[8] << 8) | modbus_rx_buffer[7]; // LSB is at index 7
      uint16_t calculated_crc =
          crc16(modbus_rx_buffer, 7); // Calculate for first 7 bytes

      if (received_crc == calculated_crc) {
        // 1. Extract the High Word (First register received: 0x602C)
        // Modbus buffer index 3 and 4 contain the first register data
        uint16_t high_word = (modbus_rx_buffer[3] << 8) | modbus_rx_buffer[4];

        // 2. Extract the Low Word (Second register received: 0x602D)
        // Modbus buffer index 5 and 6 contain the second register data
        uint16_t low_word = (modbus_rx_buffer[5] << 8) | modbus_rx_buffer[6];

        // 3. Merge them into a signed 32-bit integer
        // We shift the High Word 16 bits to the left, then OR it with the Low
        // Word.
        int32_t full_position = (int32_t)((high_word << 16) | low_word);

        // 4. Store in your global variable
        g_encoder_position = full_position;
        g_new_data_ready = 1;
      } else {
        // CRC FAILED
        g_crc_failed = 1; // Set flag for CRC error print
      }
    }

    // 4. IMPORTANT: Restart DMA listening
    HAL_UARTEx_ReceiveToIdle_DMA(&huart1, modbus_rx_buffer,
                                 MODBUS_RX_BUFFER_SIZE);
  }
}
/* USER CODE END 0 */

/**
 * @brief  The application entry point.
 * @retval int
 */
int main(void) {

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick.
   */
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
  MX_USART1_UART_Init();
  /* USER CODE BEGIN 2 */

  // NEW FRAME for Registers 0x602C & 0x602D
  uint8_t base_frame[6] = {0x01, 0x03, 0x60, 0x2C, 0x00, 0x02};

  /* Breakdown:
     0x01 : Slave ID
     0x03 : Read Command
     0x60 : Start Address High Byte
     0x2C : Start Address Low Byte  (Targeting Pr8.44)
     0x00 : Length High Byte
     0x02 : Length Low Byte (We want 2 registers: 602C and 602D)
  */
  crc = crc16(base_frame, 6);
  memcpy(enc_request_frame, base_frame, 6);
  enc_request_frame[6] = (crc & 0xFF); // LSB
  enc_request_frame[7] = (crc >> 8);   // MSB

  // --- 2. Start DMA Listening ---
  if (HAL_UARTEx_ReceiveToIdle_DMA(&huart1, modbus_rx_buffer,
                                   MODBUS_RX_BUFFER_SIZE) != HAL_OK) {
    Error_Handler();
  }

  // --- 3. Print Startup Message to Debug (USART2) ---
  sprintf(g_usart2_buffer, "--- Polling Started (Safe ISR) ---\r\n");
  HAL_UART_Transmit(&huart2, (uint8_t *)g_usart2_buffer,
                    strlen(g_usart2_buffer), HAL_MAX_DELAY);
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1) {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
    sprintf(g_usart2_buffer, "hi \r\n");
    HAL_UART_Transmit(&huart2, (uint8_t *)g_usart2_buffer,
                      strlen(g_usart2_buffer), 100);

    // --- 1. Transmit the Request ---
    HAL_UART_Transmit(&huart1, (uint8_t *)enc_request_frame, 8, 100);

    // --- 2. Wait for TX to Complete ---
    while (HAL_UART_GetState(&huart1) == HAL_UART_STATE_BUSY_TX) {
      // Wait for HAL_UART_Transmit to finish
    }

    // --- 3. Check Flags and Print (ALL PRINTING IS HERE) ---

    // Check if the ISR received *anything*
    if (g_callback_received) {
      g_callback_received = 0; // Clear the flag

      // Print the raw packet we received
      sprintf(g_usart2_buffer, "Callback! Size: %u, Data: ", g_callback_size);
      HAL_UART_Transmit(&huart2, (uint8_t *)g_usart2_buffer,
                        strlen(g_usart2_buffer), 100);

      for (int i = 0; i < g_callback_size; i++) {
        sprintf(g_usart2_buffer, "0x%02X ", g_debug_rx_buffer[i]);
        HAL_UART_Transmit(&huart2, (uint8_t *)g_usart2_buffer,
                          strlen(g_usart2_buffer), 100);
      }
      HAL_UART_Transmit(&huart2, (uint8_t *)"\r\n", 2, 100);
    }

    // Check if the ISR reported a CRC failure
    if (g_crc_failed) {
      g_crc_failed = 0; // Clear the flag
      sprintf(g_usart2_buffer, "CRC FAILED!\r\n");
      HAL_UART_Transmit(&huart2, (uint8_t *)g_usart2_buffer,
                        strlen(g_usart2_buffer), 100);
    }

    // Check if the ISR reported good data
    if (g_new_data_ready) {
      g_new_data_ready = 0; // Clear the flag

      // Print the parsed 32-bit position
      sprintf(g_usart2_buffer, "Encoder Position: %ld\r\n", g_encoder_position);
      HAL_UART_Transmit(&huart2, (uint8_t *)g_usart2_buffer,
                        strlen(g_usart2_buffer), 100);
    }

    // --- 4. Polling Delay ---
    HAL_Delay(50); // Poll 4 times per second
  }
  /* USER CODE END 3 */
}

/**
 * @brief System Clock Configuration
 * @retval None
 */
void SystemClock_Config(void) {
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
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
   */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                                RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK) {
    Error_Handler();
  }
}

/**
 * @brief USART1 Initialization Function
 * @param None
 * @retval None
 */
static void MX_USART1_UART_Init(void) {

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
  if (HAL_UART_Init(&huart1) != HAL_OK) {
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
static void MX_USART2_UART_Init(void) {

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
  if (HAL_UART_Init(&huart2) != HAL_OK) {
    Error_Handler();
  }
  /* USER CODE BEGIN USART2_Init 2 */

  /* USER CODE END USART2_Init 2 */
}

/**
 * Enable DMA controller clock
 */
static void MX_DMA_Init(void) {

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
static void MX_GPIO_Init(void) {
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  /* USER CODE BEGIN MX_GPIO_Init_1 */

  /* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOH_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();

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

/* USER CODE END 4 */

/**
 * @brief  This function is executed in case of error occurrence.
 * @retval None
 */
void Error_Handler(void) {
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1) {
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
void assert_failed(uint8_t *file, uint32_t line) {
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line
     number, ex: printf("Wrong parameters value: file %s on line %d\r\n", file,
     line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
