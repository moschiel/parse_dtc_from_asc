
# parse_dtc_from_asc

**Description**: Parse J1939 Diagnostics Trouble Code (DTC) from CANalyzer ASC logging file.

## Overview

This script processes J1939 Diagnostic Trouble Code (DTC) messages from a CANalyzer ASC logging file, specifically focusing on messages with PGN 0xFECA (DM1). It can handle both single-frame and multi-frame (BAM) messages and maintains a list of active faults, removing them if they are not seen for a specified timeout period.

## Features

- Parse single-frame DM1 messages.
- Parse multi-frame DM1 messages using BAM (Broadcast Announce Message).
- Maintain a list of active faults, adding new faults and removing those that are inactive for a specified period.
- Emulate real-time processing based on timestamps in the log file.

## Usage

1. Set the `file_path` variable to the path of your ASC log file.
2. Adjust the print control variables as needed:
   - `PRINT_DM1_SINGLE_FRAME`: Print single-frame DM1 messages.
   - `PRINT_TP_CT`: Print TP.CT messages.
   - `PRINT_TP_DT`: Print TP.DT messages.
   - `PRINT_J1939TP_FECAp`: Print concatenated J1939TP FECA messages.
   - `PRINT_TP_DM1_MULTI_FRAME`: Print multi-frame DM1 messages.
   - `PRINT_INCORRET_ORDER`: Print a message when packet order is incorrect.
   - `PRINT_DM1_PARSED`: Print parsed DM1 messages.
   - `PRINT_ACTIVE_DTCs`: Print active DTCs list.

3. Run the script.

## Output Format

### When only `PRINT_DM1_PARSED` is active:

```
DM1 -> Time: 110.945338, SRC: 0x03 (3), MIL: 3, RSL: 1, AWL: 1, PL: 0
        DTC[1] -> SPN: 0xBE (190), FMI: 8, CM: 0, OC: 2
        DTC[2] -> SPN: 0x201 (513), FMI: 8, CM: 0, OC: 2
        DTC[3] -> SPN: 0xBD2 (3026), FMI: 4, CM: 0, OC: 7
        DTC[4] -> SPN: 0xD1D (3357), FMI: 8, CM: 0, OC: 2
        DTC[5] -> SPN: 0x5C (92), FMI: 8, CM: 0, OC: 2
        DTC[6] -> SPN: 0x208 (520), FMI: 8, CM: 0, OC: 2
        DTC[7] -> SPN: 0x6E (110), FMI: 8, CM: 0, OC: 2
        DTC[8] -> SPN: 0x6C (108), FMI: 8, CM: 0, OC: 2
```

###  When `EMULATE_TIME` and `PRINT_ACTIVE_DTCs` is active:

- New faults are printed as:
  ```
  {timestamp} new fault SRC: 0x{src} ({int(src, 16)}), SPN: 0x{format(spn, 'X')} ({spn}), FMI: {fmi}
  ```

- Removed faults are printed as:
  ```
  {timestamp} removed fault SRC: 0x{fault['src']} ({int(fault['src'], 16)}), SPN: 0x{format(fault['spn'], 'X')} ({fault['spn']}), FMI: {fault['fmi']}
  ```

- Active faults list is printed as:
  ```
  Active Faults:
        SRC: 0x{fault['src']} ({int(fault['src'], 16)}), SPN: 0x{format(fault['spn'], 'X')} ({fault['spn']}), FMI: {fault['fmi']}
  ```

## Example Run

To emulate the log processing time and manage active faults list:

```python
EMULATE_TIME = True  # Enable time emulation
fault_timeout = 50   # Set the timeout for removing inactive faults

# Call the function with the path to the log file
file_path = 'example_files/VWConstel2024_1.asc'
read_log_and_print_dtc(file_path)
```

This will process the log file, parse the DTC messages, manage the active faults list, and print the results based on the specified print control variables.
