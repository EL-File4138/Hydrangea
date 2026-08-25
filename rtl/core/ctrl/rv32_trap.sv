`default_nettype none

module rv32_trap (
    input rv32_trap_pkg::trap_req_t        trap_i,
    input logic                     [31:0] pc_i,

    output logic [11:0] csr_raddr_o [2],
    input  logic [31:0] csr_rdata_i [2],
    input  logic        csr_rlegal_i[2],

    output rv32_csr_pkg::csr_write_t csr_wr_o      [4],
    input  logic                     csr_wr_legal_i[4],

    output logic        pc_valid_o,
    output logic [31:0] pc_o,

    output logic legal_o
);

  logic [31:0] mstatus_next;

  always_comb begin
    pc_valid_o = 0;
    legal_o = 0;

    pc_o = '0;
    mstatus_next = '0;

    for (int i = 0; i < 4; i++) begin
      csr_wr_o[i] = '0;
    end

    csr_raddr_o[0] = rv32_csr_pkg::MSTATUS;
    csr_raddr_o[1] = rv32_csr_pkg::MTVEC;

    if (csr_rlegal_i[0] && csr_rlegal_i[1]) begin
      mstatus_next        = csr_rdata_i[0];
      mstatus_next[7]     = csr_rdata_i[0][3];  // MPIE <- MIE
      mstatus_next[3]     = 1'b0;  // MIE  <- 0
      mstatus_next[12:11] = 2'b11;  // MPP  <- M

      pc_o                = {csr_rdata_i[1][31:2], 2'b00};

      if (trap_i.valid) begin
        csr_wr_o[0].en = 1;
        csr_wr_o[0].addr = rv32_csr_pkg::MEPC;
        csr_wr_o[0].wdata = pc_i;

        csr_wr_o[1].en = 1;
        csr_wr_o[1].addr = rv32_csr_pkg::MCAUSE;
        csr_wr_o[1].wdata = {trap_i.interrupt, trap_i.code};

        csr_wr_o[2].en = 1;
        csr_wr_o[2].addr = rv32_csr_pkg::MTVAL;
        csr_wr_o[2].wdata = trap_i.tval;

        csr_wr_o[3].en = 1;
        csr_wr_o[3].addr = rv32_csr_pkg::MSTATUS;
        csr_wr_o[3].wdata = mstatus_next;

        if (csr_wr_legal_i[0] && csr_wr_legal_i[1] && csr_wr_legal_i[2] && csr_wr_legal_i[3]) begin
          pc_valid_o = 1;
          legal_o = 1;
        end
      end
    end

  end

endmodule : rv32_trap

`default_nettype wire
