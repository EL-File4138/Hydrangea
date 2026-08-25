package rv32_inst_pkg;

  typedef enum logic [2:0] {
    R,
    I,
    S,
    B,
    U,
    J
  } inst_fmt_t;

  typedef enum logic [1:0] {
    BYTE = 2'b00,
    HALF = 2'b01,
    WORD = 2'b10
  } mem_op_width_t;

  typedef enum logic {
    SIGNED   = 0,
    UNSIGNED = 1
  } load_sign_t;

  typedef enum logic [3:0] {  // {func7[5], funct3}
    ALU_Add  = 4'b0000,
    ALU_Sub  = 4'b1000,
    ALU_Sll  = 4'b0001,
    ALU_Slt  = 4'b0010,
    ALU_Sltu = 4'b0011,
    ALU_Xor  = 4'b0100,
    ALU_Srl  = 4'b0101,
    ALU_Sra  = 4'b1101,
    ALU_Or   = 4'b0110,
    ALU_And  = 4'b0111
  } alu_op_t;
  // op == 19: I, op == 51: R;
  // Micro op only diff by func

  typedef enum logic [3:0] {  // {op[5], funct3}
    LSU_Lb  = 4'b0000,
    LSU_Lh  = 4'b0001,
    LSU_Lw  = 4'b0010,
    LSU_Lbu = 4'b0100,
    LSU_Lhu = 4'b0101,
    LSU_Sb  = 4'b1000,
    LSU_Sh  = 4'b1001,
    LSU_Sw  = 4'b1010
  } lsu_op_t;
  // op == 3: I, op == 35: S;
  // mem_op_width extracts [1:0];
  // load_sign extracts [2];
  // Load/Store extracts [3]

  typedef enum logic [2:0] {
    CTRL_Beq  = 3'b000,
    CTRL_Bne  = 3'b001,
    CTRL_Blt  = 3'b100,
    CTRL_Bge  = 3'b101,
    CTRL_Bltu = 3'b110,
    CTRL_Bgeu = 3'b111,
    CTRL_Jalr = 3'b010,
    CTRL_Jal  = 3'b011
  } ctrl_op_t;
  // op == 99: B, op == 103: I, op == 111: J;

  typedef enum logic [2:0] {  // funct3
    CSR_SYS = 3'b000,
    CSR_RW  = 3'b001,
    CSR_RS  = 3'b010,
    CSR_RC  = 3'b011,
    CSR_RWI = 3'b101,
    CSR_RSI = 3'b110,
    CSR_RCI = 3'b111
  } csr_op_t;
  // op == 115: I
  // Immediate (rs1 reinterpret) extract [2]

  typedef enum logic [2:0] {
    WB_ALU,
    WB_LSU,
    WB_CTRL,
    WB_IMM,
    WB_CSR
  } wb_src_t;

  typedef enum logic [1:0] {
    PC_SEQ,
    PC_CTRL,
    PC_CSR
  } pc_src_t;

  typedef struct packed {
    logic [4:0] rs1;
    logic [4:0] rs2;
    logic [4:0] rd;

    logic rs1_used;
    logic rs2_used;
    logic rd_write;

    logic [31:0] imm;

    alu_op_t  alu_op;
    ctrl_op_t ctrl_op;
    lsu_op_t  lsu_op;
    csr_op_t  csr_op;

    logic [4:0] csr_uimm;

    wb_src_t wb_src;
    pc_src_t pc_src;
  } inst_sem_t;

endpackage : rv32_inst_pkg
