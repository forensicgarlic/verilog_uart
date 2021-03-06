`default_nettype none
`timescale 1ns/1ps
  
// period = 12 Mhz / desired frequency
module div 
  #(parameter PERIOD=12000000,
    parameter PULSE_POINT=12000000) 
   (input wire clk_in,
    input wire clk_en,
    output reg pulse_out);

   localparam WIDTH = $clog2 (PERIOD);
   reg [WIDTH - 1 : 0] cnt=0;
   
   initial begin
      $display ("divider %m period set to %d with pulse point %d", PERIOD, PULSE_POINT);
      //simple immediate assertions not supported by iverilog 10.2
      //assert (PERIOD > 1) else $error("PERIOD must be greater than 1");
      //assert (PERIOD >= PULSE_POINT) else $error("PERIOD must be greater than PULSE_POINT");
      //$dumpfile ("div.vcd");
      //$dumpvars(0, div);
   end

   always @ (posedge clk_in)
      if (clk_en == 1 ) begin
         cnt <= (cnt == PERIOD-1) ? 0 : cnt + 1;
         pulse_out <= (cnt == PULSE_POINT -1);
       end 
       else begin
          cnt <= PERIOD -1;
          pulse_out <= 0;
       end

endmodule // div

