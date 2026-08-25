`default_nettype none
import rv32_csr_pkg::*;

module rv32_csrreg #(
    parameter int unsigned ReadPorts  = 4,
    parameter int unsigned WritePorts = 8
) (
    input logic clk_i,
    input logic rst_ni,

    input logic [11:0] rd_addr_i[ReadPorts],

    input logic       wr_en_i,
    input csr_write_t wr_i   [WritePorts],

    output logic        rd_legal_o[ ReadPorts],
    output logic        wr_legal_o[WritePorts],
    output logic [31:0] rd_data_o [ ReadPorts]
);

  import rv32_csr_impl_pkg::*;

  logic [31:0] reg_cell[NUM_CSRS];

  csr_rsp_t rd_rsp[ReadPorts];
  csr_rsp_t wr_rsp[WritePorts];

  always_comb begin  // Read comb check
    for (int r = 0; r < ReadPorts; r++) begin
      csr_req_t req;

      req           = '0;
      req.wr_en     = 1'b0;

      rd_rsp[r]     = csr_dispatch(rd_addr_i[r], req, reg_cell);
      rd_legal_o[r] = rd_rsp[r].legal;
      rd_data_o[r]  = rd_rsp[r].rdata;
    end
  end

  logic atomic_write_legal;

  always_comb begin  // Write comb check
    atomic_write_legal = 1'b1;

    // 1. Resolve every write request.
    for (int w = 0; w < WritePorts; w++) begin
      csr_req_t req;

      req = '0;
      req.wr_en = wr_i[w].en;
      req.wdata = wr_i[w].wdata;

      wr_rsp[w] = csr_dispatch(wr_i[w].addr, req, reg_cell);

      wr_legal_o[w] = wr_rsp[w].legal;
    end

    // 2. Every enabled lane must represent a legal CSR write.
    for (int w = 0; w < WritePorts; w++) begin
      if (wr_i[w].en && !wr_rsp[w].legal) begin
        atomic_write_legal = 1'b0;
      end
    end

    // 3. An atomic transaction may not write one physical CSR twice.
    for (int a = 0; a < WritePorts; a++) begin
      for (int b = a + 1; b < WritePorts; b++) begin
        if (
                wr_i[a].en &&
                wr_i[b].en &&
                wr_rsp[a].cell_valid &&
                wr_rsp[b].cell_valid &&
                wr_rsp[a].cell_idx == wr_rsp[b].cell_idx
            )
          begin
            atomic_write_legal = 1'b0;
          end
      end
    end
  end

  // Reset
  localparam csr_addr_t CsrAddrByCell[NUM_CSRS] =
      '{MSTATUS, MISA, MIE, MTVEC, MSTATUSH, MSCRATCH, MEPC, MCAUSE, MTVAL, MIP,
        MVENDORID, MARCHID, MIMPID, MHARTID, MCONFIGPTR};

  csr_rsp_t rst_rsp[NUM_CSRS];

  always_comb begin
    for (int c = 0; c < NUM_CSRS; c++) begin
      csr_req_t req;

      req = '0;
      req.rst_en = 1'b1;

      rst_rsp[c] = csr_dispatch(CsrAddrByCell[c], req, reg_cell);
    end
  end

  always_ff @(posedge clk_i) begin  // Seq execution
    if (!rst_ni) begin  // Reset
      for (int c = 0; c < NUM_CSRS; c++) begin
        reg_cell[c] <= rst_rsp[c].next;
      end
    end else if (wr_en_i && atomic_write_legal) begin  // Write
      for (int w = 0; w < WritePorts; w++) begin
        if (wr_i[w].en) begin
          reg_cell[wr_rsp[w].cell_idx] <= wr_rsp[w].next;
        end
      end
    end
  end

  function automatic csr_rsp_t csr_dispatch(input logic [11:0] addr, input csr_req_t req,
                                            const ref logic [31:0] reg_cell[NUM_CSRS]);
    csr_rsp_t a;

    a = '0;
    unique case (addr)
      MSTATUS: begin
        a            = csr_mstatus(req, reg_cell[IDX_MSTATUS]);
        a.cell_valid = 1'b1;
        a.cell_idx   = IDX_MSTATUS;
      end
      MISA: begin
        a            = csr_misa(req, reg_cell[IDX_MISA]);
        a.cell_valid = 1'b1;
        a.cell_idx   = IDX_MISA;
      end
      MIE: begin
        a            = csr_mie(req, reg_cell[IDX_MIE]);
        a.cell_valid = 1'b1;
        a.cell_idx   = IDX_MIE;
      end
      MTVEC: begin
        a            = csr_mtvec(req, reg_cell[IDX_MTVEC]);
        a.cell_valid = 1'b1;
        a.cell_idx   = IDX_MTVEC;
      end
      MSTATUSH: begin
        a            = csr_mstatush(req, reg_cell[IDX_MSTATUSH]);
        a.cell_valid = 1'b1;
        a.cell_idx   = IDX_MSTATUSH;
      end
      MSCRATCH: begin
        a            = csr_mscratch(req, reg_cell[IDX_MSCRATCH]);
        a.cell_valid = 1'b1;
        a.cell_idx   = IDX_MSCRATCH;
      end
      MEPC: begin
        a            = csr_mepc(req, reg_cell[IDX_MEPC]);
        a.cell_valid = 1'b1;
        a.cell_idx   = IDX_MEPC;
      end
      MCAUSE: begin
        a            = csr_mcause(req, reg_cell[IDX_MCAUSE]);
        a.cell_valid = 1'b1;
        a.cell_idx   = IDX_MCAUSE;
      end
      MTVAL: begin
        a            = csr_mtval(req, reg_cell[IDX_MTVAL]);
        a.cell_valid = 1'b1;
        a.cell_idx   = IDX_MTVAL;
      end
      MIP: begin
        a            = csr_mip(req, reg_cell[IDX_MIP]);
        a.cell_valid = 1'b1;
        a.cell_idx   = IDX_MIP;
      end
      MVENDORID: begin
        a            = csr_mvendorid(req, reg_cell[IDX_MVENDORID]);
        a.cell_valid = 1'b1;
        a.cell_idx   = IDX_MVENDORID;
      end
      MARCHID: begin
        a            = csr_marchid(req, reg_cell[IDX_MARCHID]);
        a.cell_valid = 1'b1;
        a.cell_idx   = IDX_MARCHID;
      end
      MIMPID: begin
        a            = csr_mimpid(req, reg_cell[IDX_MIMPID]);
        a.cell_valid = 1'b1;
        a.cell_idx   = IDX_MIMPID;
      end
      MHARTID: begin
        a            = csr_mhartid(req, reg_cell[IDX_MHARTID]);
        a.cell_valid = 1'b1;
        a.cell_idx   = IDX_MHARTID;
      end
      MCONFIGPTR: begin
        a            = csr_mconfigptr(req, reg_cell[IDX_MCONFIGPTR]);
        a.cell_valid = 1'b1;
        a.cell_idx   = IDX_MCONFIGPTR;
      end

      default: a = '0;
    endcase

    return a;
  endfunction : csr_dispatch

endmodule : rv32_csrreg

`default_nettype wire
