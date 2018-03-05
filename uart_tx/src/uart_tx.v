`default_nettype none
`include "../src/baudgen.vh"


  module uart_tx
    #(parameter BAUD=`B115200)
   ( input wire clk,
     input wire rstn,
     input wire i_start,
     input wire [7:0] i_data,
     output reg o_tx,
     output reg o_ready
     );

   reg [7:0] 	data_q = 0;
   reg 		start_q = 0;
   reg [9:0] 	shifter = 10'h2ff;
   reg [3:0] 	counter = 0;
   reg [2:0] 	state = 0;
   reg 		baud_en = 0;
   wire 	clk_baud;
   reg 		load = 0;

   
   localparam DEFAULT_DATA = 10'h2FF;

   initial begin
      $dumpfile("uart_tx.vcd");
      $dumpvars(0, uart_tx);
   end

   // register inputs and outputs
   always @ (posedge clk) begin
      if (i_start == 1 && state == IDLE) begin
	data_q <= i_data;
      end
      start_q <= i_start;
      o_tx <= shifter[0];
   end

   // shift register
   always @ (posedge clk or negedge rstn) begin
      if (rstn == 0)
	shifter <= DEFAULT_DATA;
      else if (load == 1)
	shifter <= {data_q, 2'b01};
      else if ( clk_baud == 1)
	shifter <= {1'b1, shifter[9:1]};
   end

   div #(BAUD,BAUD)
   baudgen (.clk_in(clk), .clk_en(baud_en), .pulse_out(clk_baud));

   // state machine counter
   always @ (posedge clk) begin
      if (load == 1)
	counter <= 0;
      else if (clk_baud == 1)
	counter <= counter + 1;
   end

   // State Machine
   localparam IDLE = 3'b001;
   localparam START = 3'b010;
   localparam TRANSMIT = 3'b100;
   always @ (posedge clk or negedge rstn) begin
      if (rstn == 0) begin
	 state <= IDLE;
	 load <= 0;
	 o_ready <= 0;
	 baud_en <= 0;
      end
      else begin
	 case(state)
	   IDLE:
	     begin
		if (i_start == 1) begin
		   state <= START;
		   load <= 1;
		   o_ready <= 0;
		   baud_en <= 1;
		end else begin
		   load <=0;
		   o_ready <= 1;
		   baud_en <= 0;
		end
	     end
	   
	   START:
	     begin
		state <= TRANSMIT;
		baud_en <= 1;
		load <= 0;
		o_ready <= 0;
	     end
	   TRANSMIT:
	     begin
		if (counter == 11) begin
		   state <= IDLE;
		   baud_en <= 0;
		end else begin
		   baud_en <= 1;
		   state <= TRANSMIT;
		end
		o_ready <= 0;
		load <= 0;
	     end
	   default:
	     begin
		state <= IDLE;
		load <= 0;
		o_ready <= 0;
		baud_en <= 0;
	     end
	 endcase
      end // not in reset
   end // always @ (posedge clk)
endmodule // uart_tx
