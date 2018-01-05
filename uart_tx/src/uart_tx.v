`default_nettype none
`include "../src/baudgen.vh"


  module uart_tx
    #(parameter BAUD=`B115200)
   ( input wire clk,
     input wire rstn,
     input wire start,
     input wire [7:0] data,
     output reg tx,
     output reg ready
     );

   reg [7:0] 	data_q;
   reg 		start_q;
   reg [9:0] 	shifter;
   reg [3:0] 	counter = 0;
   reg [2:0] 	state;
   reg 		baud_en;
   wire 	clk_baud;
   reg 		load;
   


   localparam DEFAULT_DATA = 10'h2FF;
   
   // register inputs and outputs
   always @ (posedge clk) begin
      if (start == 1 && state == IDLE) begin
	data_q <= data;
      end
      start_q <= start;
      tx <= shifter[0];
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
   
   div #(BAUD) 
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
   always @ (posedge clk) begin
      case(state)
	IDLE:
	  begin
	     if (start == 1) begin
		state <= START;
		load <= 1;
		baud_en <= 1;
	     end else begin
		load <=0;
		baud_en <= 0;
	     end
	  end
	
	START:
	  begin
	     state <= TRANSMIT;
	     baud_en <= 1;
	     load <= 0;
	     
	  end
	TRANSMIT:
	  begin
	     if (counter == 11) begin
		state <= IDLE;
		load <= 0;
		baud_en <= 0;
	     end else begin
		load <= 0;
		baud_en <= 1;
	     end
	     
	  end
	
	default:
	  begin
	     state <= IDLE;
	     load <= 0;
	     baud_en <= 0;
	  end
	
      endcase
      
   end // always @ (posedge clk)
endmodule // uart_tx
