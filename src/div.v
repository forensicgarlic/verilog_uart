`default_nettype none
`timescale 1ns/1ps
  
// period = 12 Mhz / desired frequency
module div #(parameter PERIOD=12000000) (input wire clk_in, output wire clk_out);
   localparam WIDTH = $clog2 (PERIOD);
   reg [WIDTH - 1 : 0] cnt=0;
   initial begin
      $display ("divider %m period set to %d", PERIOD);
      //simple immediate assertions not supported by iverilog 10.2
      //assert (PERIOD > 1) else $error("PERIOD must be greater than 1");
   end
   
   always @ (posedge clk_in)
     if (cnt == PERIOD-1)
       cnt <= 0;
     else
       cnt <= cnt + 1;

   assign clk_out = cnt[WIDTH-1];
endmodule // div

