/* Linker script: current default direct-preload simulation profile.
 *
 * Profile-resolved values (execution-environment contract, Section 3.2):
 *   ResetVector         = 0x0000_0000
 *   Unified RAM (rwx)   = 0x0000_0000 .. 0x0003_FFFF (256 KiB)
 *   Entry               = _start, linked at ResetVector (direct entry)
 *   Stack               = reserved .stack region inside writable memory,
 *                         16-byte aligned, non-overlapping with the image
 * Load addresses equal run addresses; no relocation or copying.
 */

OUTPUT_ARCH(riscv)
ENTRY(_start)

MEMORY
{
    RAM (rwx) : ORIGIN = 0x00000000, LENGTH = 0x00040000
}

STACK_SIZE = 0x1000;

SECTIONS
{
    .text :
    {
        KEEP(*(.text.start))
        *(.text .text.*)
    } > RAM

    .rodata :
    {
        *(.rodata .rodata.*)
        *(.srodata .srodata.*)
    } > RAM

    .data : ALIGN(4)
    {
        __data_start = .;
        *(.data .data.*)
        *(.sdata .sdata.*)
        __data_end = .;
    } > RAM

    PROVIDE(__global_pointer$ = __data_start + 0x800);

    .bss (NOLOAD) : ALIGN(4)
    {
        __bss_start = .;
        *(.bss .bss.*)
        *(.sbss .sbss.*)
        *(COMMON)
        __bss_end = .;
    } > RAM

    .stack (NOLOAD) : ALIGN(16)
    {
        . += STACK_SIZE;
        __stack_top = .;
    } > RAM

    /DISCARD/ :
    {
        *(.eh_frame .eh_frame_hdr)
        *(.comment)
        *(.note .note.*)
        *(.riscv.attributes)
    }
}

/* Direct-entry profiles link the startup entry at the reset target. */
ASSERT(_start == ORIGIN(RAM),
    "_start shall equal the profile ResetVector (direct entry)")
ASSERT((__bss_end - __bss_start) % 4 == 0, ".bss shall be word aligned")
ASSERT(__stack_top % 16 == 0, "stack top shall be 16-byte aligned")
