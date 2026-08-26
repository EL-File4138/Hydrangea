package rv32_csr_pkg;

  typedef enum logic [2:0] {
    RW,
    RO,
    WPRI,
    WARL,
    WLRL
  } csr_semantics_e;

  typedef enum logic [11:0] {
    MSTATUS    = 12'h300,
    MISA       = 12'h301,
    MIE        = 12'h304,
    MTVEC      = 12'h305,
    MSTATUSH   = 12'h310,
    MSCRATCH   = 12'h340,
    MEPC       = 12'h341,
    MCAUSE     = 12'h342,
    MTVAL      = 12'h343,
    MIP        = 12'h344,
    MVENDORID  = 12'hF11,
    MARCHID    = 12'hF12,
    MIMPID     = 12'hF13,
    MHARTID    = 12'hF14,
    MCONFIGPTR = 12'hF15
  } csr_address_e;

  typedef enum int unsigned {
    IDX_MSTATUS,
    IDX_MISA,
    IDX_MIE,
    IDX_MTVEC,
    IDX_MSTATUSH,
    IDX_MSCRATCH,
    IDX_MEPC,
    IDX_MCAUSE,
    IDX_MTVAL,
    IDX_MIP,
    IDX_MVENDORID,
    IDX_MARCHID,
    IDX_MIMPID,
    IDX_MHARTID,
    IDX_MCONFIGPTR,
    CSR_COUNT
  } csr_index_e;

  typedef struct packed {
    logic        write_enable;
    logic        reset_enable;
    logic [31:0] write_data;
  } csr_req_t;

  typedef struct packed {
    logic        is_legal;
    logic [31:0] read_data;
    logic [31:0] value_candidate;

    csr_index_e cell_index;
    logic       cell_is_valid;
  } csr_rsp_t;

  typedef struct packed {
    logic        write_enable;
    logic [11:0] address;
    logic [31:0] write_data;
  } csr_write_t;
endpackage : rv32_csr_pkg
