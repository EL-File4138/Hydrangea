/* Startup code for the default direct-preload simulation profile.
 *
 * Linked at the profile ResetVector (0x00000000). Establishes the C runtime
 * required by the execution-environment contract, Section 6: sp (16-byte
 * aligned via the linker), gp, zeroed .bss (.data is linked in its initial
 * state with load == run addresses), then enters main per the RV32 ILP32
 * calling convention. No mtvec setup is needed before trap dependency.
 */

    .section .text.start, "ax", @progbits
    .globl _start
_start:
    /* gp must be materialized without linker relaxation against itself. */
.option push
.option norelax
    la      gp, __global_pointer$
.option pop

    la      sp, __stack_top

    /* Zero .bss; __bss_start/__bss_end are word aligned by the linker. */
    la      t0, __bss_start
    la      t1, __bss_end
1:
    bgeu    t0, t1, 2f
    sw      zero, 0(t0)
    addi    t0, t0, 4
    j       1b
2:

    call    main

    /* main returned: defined local terminal loop; no exit ABI exists. */
3:
    j       3b

    .size _start, . - _start
