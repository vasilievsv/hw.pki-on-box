target remote :3333
monitor reset halt
echo USB_CNTR (0x40005C40): 
x/1xw 0x40005C40
echo RCC_CRRCR (HSI48): 
x/1xw 0x40021018
echo RCC_CCIPR (CLK48SEL): 
x/1xw 0x40021088
echo RCC_APB1ENR1 (USBEN bit20): 
x/1xw 0x40021058
monitor resume
quit
