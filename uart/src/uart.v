`default_nettype none
`include "../../uart_tx/src/baudgen.vh"


module uart
  #(parameter BAUD=`B115200)
   (input wire clk,
    input wire rstn,
    input wire i_rx,
    input wire i_tx_start,
    input wire [7:0] i_tx_data,
    output reg [7:0] o_rx_data,
    output reg o_rx_data_valid,
    output reg o_tx,
    output_reg o_tx_ready
    );

   initial begin
      $dumpfile("uart.vcd");
      $dumpvars(0, uart);
   end

   uart_rx #(BAUD)
   uart_rx_inst (.clk(clk), .rstn(rstn), .i_rx(i_rx), .o_data(o_rx_data), .o_rcv(o_rx_data_valid));

   uart_tx #(BAUD)
   uart_tx_inst(.clk(clk), .rstn(rstn), .i_start(i_tx_start), .i_data(i_tx_data), .o_tx(o_tx), .o_ready(o_tx_ready));

endmodule // uart
