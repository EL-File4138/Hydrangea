`default_nettype none

// Maps independent instruction and data interfaces onto one single-port RAM.
// By default both paths expose the same 256 KiB unified-RAM window at address 0.
// Region bases must be word aligned so an architectural word remains a RAM word.
module rv32_shared_sync_ram_adapter #(
    parameter int unsigned AddrWidth = 16,
    parameter logic [31:0] UnifiedRamBaseAddr = 32'h0000_0000,
    parameter logic [31:0] UnifiedRamSizeBytes = (32'd1 << (AddrWidth + 2)),
    parameter logic [31:0] ImemBaseAddr = UnifiedRamBaseAddr,
    parameter logic [31:0] ImemSizeBytes = UnifiedRamSizeBytes,
    parameter logic [31:0] DmemBaseAddr = UnifiedRamBaseAddr,
    parameter logic [31:0] DmemSizeBytes = UnifiedRamSizeBytes
) (
    input logic clk_i,
    input logic rst_ni,

    rv32_mem_if.responder imem_if_i,
    rv32_mem_if.responder dmem_if_i
);

  typedef enum logic [1:0] {
    RAM_STATE_IDLE,
    RAM_STATE_ACCESS,
    RAM_STATE_RESPOND,
    RAM_STATE_WAIT_FOR_REQUEST_DROP
  } ram_state_e;

  ram_state_e state_q;
  ram_state_e state_d;
  logic owner_is_imem_q;
  logic [31:0] local_addr_q;
  logic write_q;
  logic [31:0] wdata_q;
  logic [3:0] wstrb_q;
  logic err_q;

  logic ram_write_enable;
  logic [31:0] ram_write_data;
  rv32_inst_pkg::mem_width_e ram_write_type;
  logic [31:0] ram_read_data;

  function automatic logic address_is_mapped(
      input logic [31:0] addr,
      input logic [31:0] base,
      input logic [31:0] size
  );
    logic [32:0] addr_ext;
    logic [32:0] base_ext;
    logic [32:0] end_ext;

    addr_ext = {1'b0, addr};
    base_ext = {1'b0, base};
    end_ext = base_ext + {1'b0, size};
    return (size != 32'd0) && (addr_ext >= base_ext) && (addr_ext < end_ext);
  endfunction

  function automatic logic write_strobes_are_valid(
      input logic write_enable,
      input logic [3:0] wstrb
  );
    if (!write_enable) begin
      return wstrb == 4'b0000;
    end

    unique case (wstrb)
      4'b0001, 4'b0010, 4'b0100, 4'b1000,
      4'b0011, 4'b1100, 4'b1111: return 1'b1;
      default: return 1'b0;
    endcase
  endfunction

  always_comb begin
    ram_write_enable = (state_q == RAM_STATE_ACCESS) && write_q;
    ram_write_data = wdata_q;
    ram_write_type = rv32_inst_pkg::MEM_WIDTH_WORD;

    unique case (wstrb_q)
      4'b0001: begin
        ram_write_data = wdata_q;
        ram_write_type = rv32_inst_pkg::MEM_WIDTH_BYTE;
      end
      4'b0010: begin
        ram_write_data = wdata_q >> 8;
        ram_write_type = rv32_inst_pkg::MEM_WIDTH_BYTE;
      end
      4'b0100: begin
        ram_write_data = wdata_q >> 16;
        ram_write_type = rv32_inst_pkg::MEM_WIDTH_BYTE;
      end
      4'b1000: begin
        ram_write_data = wdata_q >> 24;
        ram_write_type = rv32_inst_pkg::MEM_WIDTH_BYTE;
      end
      4'b0011: begin
        ram_write_data = wdata_q;
        ram_write_type = rv32_inst_pkg::MEM_WIDTH_HALF;
      end
      4'b1100: begin
        ram_write_data = wdata_q >> 16;
        ram_write_type = rv32_inst_pkg::MEM_WIDTH_HALF;
      end
      default: begin
        ram_write_data = wdata_q;
        ram_write_type = rv32_inst_pkg::MEM_WIDTH_WORD;
      end
    endcase
  end

  always_comb begin
    imem_if_i.ready = 1'b0;
    imem_if_i.rdata = 32'b0;
    imem_if_i.err = 1'b0;
    dmem_if_i.ready = 1'b0;
    dmem_if_i.rdata = 32'b0;
    dmem_if_i.err = 1'b0;

    if (state_q == RAM_STATE_RESPOND) begin
      if (owner_is_imem_q) begin
        imem_if_i.ready = 1'b1;
        imem_if_i.rdata = ram_read_data;
        imem_if_i.err = err_q;
      end else begin
        dmem_if_i.ready = 1'b1;
        dmem_if_i.rdata = ram_read_data;
        dmem_if_i.err = err_q;
      end
    end
  end

  always_comb begin
    state_d = state_q;

    unique case (state_q)
      RAM_STATE_IDLE: begin
        if (imem_if_i.req) begin
          if (address_is_mapped(imem_if_i.addr, ImemBaseAddr, ImemSizeBytes) &&
              !imem_if_i.we && (imem_if_i.wstrb == 4'b0000)) begin
            state_d = RAM_STATE_ACCESS;
          end else begin
            state_d = RAM_STATE_RESPOND;
          end
        end else if (dmem_if_i.req) begin
          if (address_is_mapped(dmem_if_i.addr, DmemBaseAddr, DmemSizeBytes) &&
              write_strobes_are_valid(dmem_if_i.we, dmem_if_i.wstrb)) begin
            state_d = RAM_STATE_ACCESS;
          end else begin
            state_d = RAM_STATE_RESPOND;
          end
        end
      end
      RAM_STATE_ACCESS: state_d = RAM_STATE_RESPOND;
      RAM_STATE_RESPOND: state_d = RAM_STATE_WAIT_FOR_REQUEST_DROP;
      RAM_STATE_WAIT_FOR_REQUEST_DROP: begin
        if ((owner_is_imem_q && !imem_if_i.req) ||
            (!owner_is_imem_q && !dmem_if_i.req)) begin
          state_d = RAM_STATE_IDLE;
        end
      end
      default: state_d = RAM_STATE_IDLE;
    endcase
  end

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      state_q <= RAM_STATE_IDLE;
      owner_is_imem_q <= 1'b0;
      local_addr_q <= 32'b0;
      write_q <= 1'b0;
      wdata_q <= 32'b0;
      wstrb_q <= 4'b0;
      err_q <= 1'b0;
    end else begin
      state_q <= state_d;
      unique case (state_q)
        RAM_STATE_IDLE: begin
          // The baseline core never overlaps paths; IMEM priority is deterministic
          // if this example is connected to a requester that does.
          if (imem_if_i.req) begin
            owner_is_imem_q <= 1'b1;
            local_addr_q <= imem_if_i.addr - ImemBaseAddr;
            write_q <= imem_if_i.we;
            wdata_q <= imem_if_i.wdata;
            wstrb_q <= imem_if_i.wstrb;
            if (address_is_mapped(imem_if_i.addr, ImemBaseAddr, ImemSizeBytes) &&
                !imem_if_i.we && (imem_if_i.wstrb == 4'b0000)) begin
              err_q <= 1'b0;
            end else begin
              err_q <= 1'b1;
            end
          end else if (dmem_if_i.req) begin
            owner_is_imem_q <= 1'b0;
            local_addr_q <= dmem_if_i.addr - DmemBaseAddr;
            write_q <= dmem_if_i.we;
            wdata_q <= dmem_if_i.wdata;
            wstrb_q <= dmem_if_i.wstrb;
            if (address_is_mapped(dmem_if_i.addr, DmemBaseAddr, DmemSizeBytes) &&
                write_strobes_are_valid(dmem_if_i.we, dmem_if_i.wstrb)) begin
              err_q <= 1'b0;
            end else begin
              err_q <= 1'b1;
            end
          end
        end
        default: ;
      endcase
    end
  end

  sync_ram #(
      .AddrWidth(AddrWidth)
  ) u_sync_ram (
      .clk_i(clk_i),
      .rst_ni(rst_ni),
      .write_enable_i(ram_write_enable),
      .addr_i(local_addr_q),
      .write_data_i(ram_write_data),
      .write_type_i(ram_write_type),
      .read_data_o(ram_read_data)
  );

endmodule : rv32_shared_sync_ram_adapter

`default_nettype wire
