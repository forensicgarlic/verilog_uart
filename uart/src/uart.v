`default_nettype none
`include "../../uart_tx/src/baudgen.vh"


module uart
  #(parameter BAUD=`B115200)
   (input wire clk,
    input wire rstn,
    input wire i_rx,
    input wire i_tx_start,
    input wire [7:0] i_tx_data,
    output wire [7:0] o_rx_data,
    output wire o_rx_data_valid,
    output wire o_tx,
    output wire o_tx_ready
    );


   wire [7:0]   rx_data;
   wire 	rx_data_valid;
   wire 	tx;
   wire 	tx_ready;

   assign o_rx_data = rx_data;
   assign o_rx_data_valid = rx_data_valid;
   assign o_tx = tx;
   assign o_tx_ready = tx_ready;
   
   
       
   
   initial begin
      $dumpfile("uart.vcd");
      $dumpvars(0, uart);
   end

   uart_rx #(BAUD)
   uart_rx_inst (.clk(clk), .rstn(rstn), .i_rx(i_rx), .o_data(rx_data), .o_rcv(rx_data_valid));

   uart_tx #(BAUD)
   uart_tx_inst(.clk(clk), .rstn(rstn), .i_start(i_tx_start), .i_data(i_tx_data), .o_tx(tx), .o_ready(tx_ready));

endmodule // uart
