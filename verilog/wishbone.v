`timescale 1ns/100ps

module wishbone(
    clk,             // interface side to outer world
    a_reset_l,
    wb_ack_i,
    wb_we_o,
    wb_stb_o,
    wb_cyc_o,
    wb_adr_o,
    wb_dat_i,
    wb_dat_o,
    intr_h,
    intr_ack_h,
    sync_h,
    addr_i,             // interface to chip side
    data_i,
    data_o,
    we_i,
    start_i,
    busy_o,
    valid_o,
    intr,
    intr_ack,
    sync
);
parameter data_wl = 16;
parameter adr_wl  = 16;

input   clk;

input   a_reset_l;
// signals to Wishbone
input   wb_ack_i;
output  wb_we_o;
output  wb_stb_o;
output  wb_cyc_o;
output  [adr_wl-1:0] wb_adr_o;
input   [data_wl-1:0] wb_dat_i;
output  [data_wl-1:0] wb_dat_o;

input   intr_h;
output  intr_ack_h;
input   sync_h;
// internal signals
input   [adr_wl-1:0] addr_i;
input   we_i;
input   [data_wl-1:0] data_i;
output  [data_wl-1:0] data_o;
input   start_i;
output  busy_o;
output  valid_o;

output  intr;
input   intr_ack;
output  sync;

reg     wb_we_o,  nxt_wb_we_o;
reg     wb_stb_o, nxt_wb_stb_o;
reg     wb_cyc_o, nxt_wb_cyc_o;
reg     busy_o, nxt_busy_o;
reg     valid_o, nxt_valid_o;

reg     [adr_wl-1:0] wb_adr_o, nxt_wb_adr_o;
reg     [data_wl-1:0] wb_dat_o, nxt_wb_dat_o;
reg     [data_wl-1:0] data_o, nxt_data_o;

//#########################################
assign intr         = intr_h;
assign intr_ack_h   = intr_ack;
assign sync         = sync_h;
//#########################################

reg [4:0] current_state, nxt_state;
localparam [4:0]
IDLE    = 5'b00001,
WAIT    = 5'b00010;

always @(posedge clk or negedge a_reset_l)
    begin
        if (a_reset_l == 1'b0)    
            begin
                current_state   <= IDLE;
                wb_we_o         <= 1'b0;
                wb_stb_o        <= 1'b0;
                wb_cyc_o        <= 1'b0;
                wb_adr_o        <= {adr_wl{1'b0}};
                wb_dat_o        <= {data_wl{1'b0}};
                data_o          <= {data_wl{1'b0}};
                busy_o          <= 1'b0;
                valid_o         <= 1'b0;
            end
        else
            begin
                current_state   <= nxt_state;
                wb_we_o         <= nxt_wb_we_o;
                wb_stb_o        <= nxt_wb_stb_o;
                wb_cyc_o        <= nxt_wb_cyc_o;
                busy_o          <= nxt_busy_o;
                valid_o         <= nxt_valid_o;
                wb_adr_o        <= nxt_wb_adr_o;
                wb_dat_o        <= nxt_wb_dat_o;
                data_o          <= nxt_data_o;
            end
    end

//#########################################    
always @(*)
    begin    
        nxt_state       = current_state;
        nxt_wb_we_o     = wb_we_o;
        nxt_wb_stb_o    = wb_stb_o;
        nxt_wb_cyc_o    = wb_cyc_o;
        nxt_busy_o      = busy_o;
        nxt_valid_o     = valid_o;
        nxt_wb_adr_o    = wb_adr_o;
        nxt_wb_dat_o    = wb_dat_o;
        nxt_data_o      = data_o;

        case (current_state)
            IDLE:                
                begin
                    if (start_i == 1'b1) begin
                        nxt_state       = WAIT;
                        nxt_wb_we_o     = we_i;
                        nxt_wb_stb_o    = 1'b1;
                        nxt_wb_cyc_o    = 1'b1;
                        nxt_busy_o      = 1'b1;
                        nxt_valid_o     = 1'b0;
                        nxt_wb_adr_o    = addr_i;
                        nxt_wb_dat_o    = data_i;
                    end else begin
                        nxt_state       = IDLE;
                        nxt_wb_we_o     = 1'b0;
                        nxt_wb_stb_o    = 1'b0;
                        nxt_wb_cyc_o    = 1'b0;
                    end
                end
            
            WAIT:
                begin
                    if (wb_ack_i == 1'b1) begin
                        nxt_state       = IDLE;
                        nxt_busy_o      = 1'b0;
                        nxt_valid_o     = 1'b1;  // Assert valid_o
                        nxt_data_o      = wb_dat_i;  // Latch data
                    end else begin
                        nxt_state       = WAIT;
                    end
                end
            
            default:
                begin
                    nxt_state = IDLE;
                end
        endcase
    end

initial begin
$dumpfile("dump.vcd");
$dumpvars(1,wb_interface);
end

endmodule
