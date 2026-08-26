`default_nettype none

module rv32_csr_register_bank #(
    parameter int unsigned ReadPorts  = 4,
    parameter int unsigned WritePorts = 8
) (
    input logic clk_i,
    input logic rst_ni,

    input logic [11:0] rd_addr_i[ReadPorts],

    input logic                     wr_en_i,
    input rv32_csr_pkg::csr_write_t wr_i   [WritePorts],

    output logic        rd_legal_o[ ReadPorts],
    output logic        wr_legal_o[WritePorts],
    output logic [31:0] rd_data_o [ ReadPorts]
);
  import rv32_csr_pkg::*;
  import rv32_csr_implementation_pkg::*;

  logic [31:0] reg_cell[CSR_COUNT];

  csr_rsp_t rd_rsp[ReadPorts];
  csr_rsp_t wr_rsp[WritePorts];

  always_comb begin  // Read comb check
    for (int r = 0; r < ReadPorts; r++) begin
      csr_req_t req;

      req           = '0;
      req.write_enable     = 1'b0;

      rd_rsp[r]     = csr_dispatch(rd_addr_i[r], req, reg_cell);
      rd_legal_o[r] = rd_rsp[r].is_legal;
      rd_data_o[r]  = rd_rsp[r].read_data;
    end
  end

  logic atomic_write_legal;

  always_comb begin  // Write comb check
    atomic_write_legal = 1'b1;

    // 1. Resolve every write request.
    for (int w = 0; w < WritePorts; w++) begin
      csr_req_t req;

      req = '0;
      req.write_enable = wr_i[w].write_enable;
      req.write_data = wr_i[w].write_data;

      wr_rsp[w] = csr_dispatch(wr_i[w].address, req, reg_cell);

      wr_legal_o[w] = wr_rsp[w].is_legal;
    end

    // 2. Every enabled lane must represent a legal CSR write.
    for (int w = 0; w < WritePorts; w++) begin
      if (wr_i[w].write_enable && !wr_rsp[w].is_legal) begin
        atomic_write_legal = 1'b0;
      end
    end

    // 3. An atomic transaction may not write one physical CSR twice.
    for (int a = 0; a < WritePorts; a++) begin
      for (int b = a + 1; b < WritePorts; b++) begin
        if (
                wr_i[a].write_enable &&
                wr_i[b].write_enable &&
                wr_rsp[a].cell_is_valid &&
                wr_rsp[b].cell_is_valid &&
                wr_rsp[a].cell_index == wr_rsp[b].cell_index
            )
          begin
          atomic_write_legal = 1'b0;
        end
      end
    end
  end

  // Reset
  localparam csr_address_e CsrAddrByCell[CSR_COUNT] = '{
      MSTATUS,
      MISA,
      MIE,
      MTVEC,
      MSTATUSH,
      MSCRATCH,
      MEPC,
      MCAUSE,
      MTVAL,
      MIP,
      MVENDORID,
      MARCHID,
      MIMPID,
      MHARTID,
      MCONFIGPTR
  };

  csr_rsp_t rst_rsp[CSR_COUNT];

  always_comb begin
    for (int c = 0; c < CSR_COUNT; c++) begin
      csr_req_t req;

      req = '0;
      req.reset_enable = 1'b1;

      rst_rsp[c] = csr_dispatch(CsrAddrByCell[c], req, reg_cell);
    end
  end

  always_ff @(posedge clk_i or negedge rst_ni) begin  // Seq execution
    if (!rst_ni) begin  // Reset
      for (int c = 0; c < CSR_COUNT; c++) begin
        reg_cell[c] <= rst_rsp[c].value_candidate;
      end
    end else if (wr_en_i && atomic_write_legal) begin  // Write
      for (int w = 0; w < WritePorts; w++) begin
        if (wr_i[w].write_enable) begin
          reg_cell[wr_rsp[w].cell_index] <= wr_rsp[w].value_candidate;
        end
      end
    end
  end

  function automatic csr_rsp_t csr_dispatch(input logic [11:0] addr, input csr_req_t req,
                                            const ref logic [31:0] reg_cell_ref[CSR_COUNT]);
    csr_rsp_t a;

    a = '0;
    unique case (addr)
      MSTATUS: begin
        a            = csr_mstatus(req, reg_cell_ref[IDX_MSTATUS]);
        a.cell_is_valid = 1'b1;
        a.cell_index   = IDX_MSTATUS;
      end
      MISA: begin
        a            = csr_misa(req, reg_cell_ref[IDX_MISA]);
        a.cell_is_valid = 1'b1;
        a.cell_index   = IDX_MISA;
      end
      MIE: begin
        a            = csr_mie(req, reg_cell_ref[IDX_MIE]);
        a.cell_is_valid = 1'b1;
        a.cell_index   = IDX_MIE;
      end
      MTVEC: begin
        a            = csr_mtvec(req, reg_cell_ref[IDX_MTVEC]);
        a.cell_is_valid = 1'b1;
        a.cell_index   = IDX_MTVEC;
      end
      MSTATUSH: begin
        a            = csr_mstatush(req, reg_cell_ref[IDX_MSTATUSH]);
        a.cell_is_valid = 1'b1;
        a.cell_index   = IDX_MSTATUSH;
      end
      MSCRATCH: begin
        a            = csr_mscratch(req, reg_cell_ref[IDX_MSCRATCH]);
        a.cell_is_valid = 1'b1;
        a.cell_index   = IDX_MSCRATCH;
      end
      MEPC: begin
        a            = csr_mepc(req, reg_cell_ref[IDX_MEPC]);
        a.cell_is_valid = 1'b1;
        a.cell_index   = IDX_MEPC;
      end
      MCAUSE: begin
        a            = csr_mcause(req, reg_cell_ref[IDX_MCAUSE]);
        a.cell_is_valid = 1'b1;
        a.cell_index   = IDX_MCAUSE;
      end
      MTVAL: begin
        a            = csr_mtval(req, reg_cell_ref[IDX_MTVAL]);
        a.cell_is_valid = 1'b1;
        a.cell_index   = IDX_MTVAL;
      end
      MIP: begin
        a            = csr_mip(req, reg_cell_ref[IDX_MIP]);
        a.cell_is_valid = 1'b1;
        a.cell_index   = IDX_MIP;
      end
      MVENDORID: begin
        a            = csr_mvendorid(req, reg_cell_ref[IDX_MVENDORID]);
        a.cell_is_valid = 1'b1;
        a.cell_index   = IDX_MVENDORID;
      end
      MARCHID: begin
        a            = csr_marchid(req, reg_cell_ref[IDX_MARCHID]);
        a.cell_is_valid = 1'b1;
        a.cell_index   = IDX_MARCHID;
      end
      MIMPID: begin
        a            = csr_mimpid(req, reg_cell_ref[IDX_MIMPID]);
        a.cell_is_valid = 1'b1;
        a.cell_index   = IDX_MIMPID;
      end
      MHARTID: begin
        a            = csr_mhartid(req, reg_cell_ref[IDX_MHARTID]);
        a.cell_is_valid = 1'b1;
        a.cell_index   = IDX_MHARTID;
      end
      MCONFIGPTR: begin
        a            = csr_mconfigptr(req, reg_cell_ref[IDX_MCONFIGPTR]);
        a.cell_is_valid = 1'b1;
        a.cell_index   = IDX_MCONFIGPTR;
      end

      default: a = '0;
    endcase

    return a;
  endfunction : csr_dispatch

endmodule : rv32_csr_register_bank

`default_nettype wire
