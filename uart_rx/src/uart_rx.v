`default_nettype none
`include "../../uart_tx/src/baudgen.vh"
  
  module uart_rx
    #(parameter BAUD=`B115200)
    (input wire clk,
     input wire rstn,
     input wire i_rx,
     output reg [7:0] o_data,
     output reg o_rcv
     );
   

   reg 		rx_q = 0;
   reg [9:0] 	shift_in = 0;
   wire		clk_baud;
   reg 		baud_en = 0;
   reg 		load = 0;
   reg [3:0] 	cnt = 0;
   reg 		clear = 0;
   reg [1:0] 	state = 0;
 	

   //initial begin
   //   $dumpfile("uart_rx.vcd");
   //   $dumpvars(0, uart_rx);
   //end

   // register the input
   // we could add another register here if we were
   // worried about metastability. 
   always @ (posedge clk) begin
      rx_q <= i_rx;
   end

   // shift register for the output
   always @ (posedge clk or negedge rstn) begin
      if (rstn == 0)
	shift_in <= 0;
      else if (clk_baud == 1)
	shift_in <= {rx_q, shift_in[9:1]};
   end

   // load output when we've gotten through the state machine
   always @ (posedge clk or negedge rstn) begin
      if (rstn == 0)
	o_data <= 0;
      else if (load == 1)
	o_data <= shift_in[8:1];
   end

   // baud rate pulse gen
   div #(BAUD, BAUD/2)
   baudgen (.clk_in(clk), .clk_en(baud_en), .pulse_out(clk_baud));
   
   // bit counter
   always @ (posedge clk) begin
      if (clear == 1)
	cnt <= 0;
      else if (clk_baud == 1)
	cnt <= cnt + 1;
   end

   localparam IDLE = 2'b00;
   localparam RCV  = 2'b01;
   localparam LOAD = 2'b10;
   localparam DATA_VALID = 2'b11;
   
   always @ (posedge clk or negedge rstn) begin
      if (rstn == 0) begin
	 state <= IDLE;
	 load <= 0;
	 o_rcv <= 0;
	 clear <= 0;
	 baud_en <= 0;
      end
      else
	case (state)
	  IDLE:
	    begin
	       if (rx_q == 0)
		 state <= RCV;
	       else
		 state <= IDLE;
	       load <= 0;
	       o_rcv <= 0;
	       baud_en <= 0;
	       clear <= 1;
	    end
	  RCV:
	    begin
	       if (cnt == 10 && rx_q == 1)
		 state <= LOAD;
	       else if (cnt == 10 && rx_q == 0) // break or frame error
		 state <= IDLE;
	       else if (cnt == 0 && rx_q == 1) // glitch in line
		 state <= IDLE;
	       else
		 state <= RCV;
	       load <= 0;
	       o_rcv <= 0;
	       baud_en <= 1;
	       clear <= 0;
	    end
	  LOAD:
	    begin
	       state <= DATA_VALID;
	       load <= 1;
	       o_rcv <= 0;
	       baud_en <= 0;
	       clear <= 0;
	    end
	  DATA_VALID:
	    begin
	       state <= IDLE;
	       load <= 0;
	       o_rcv <= 1;
	       baud_en <= 0;
	       clear <= 0;
	    end
	  default:
	    begin
	       state <= IDLE;
	       clear <= 0;
	       load <= 0;
	       baud_en <= 0;
	       o_rcv <= 0;
	    end
	endcase // case (state)
   end // always @ (posedge clk or negedge rstn)
endmodule // uart_rx

   
   
