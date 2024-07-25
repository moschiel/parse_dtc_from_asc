
# parse_dtc_from_asc

**Description**: Parse J1939 Diagnostics Trouble Code (DTC) from CANalyzer ASC logging file.

![image](https://github.com/user-attachments/assets/0cf920b0-2f3a-4ac5-8aae-b8e9b04ca8ec)


## Overview

This script processes J1939 Diagnostic Trouble Code (DTC) messages from a CANalyzer ASC logging file, specifically focusing on messages with PGN 0xFECA (DM1). It can handle both single-frame and multi-frame (BAM) messages and maintains a list of active faults, removing them if they are not seen for a specified timeout period. The GUI provides a real-time display of active faults, their status, and an adjustable timeout setting.

## Features

- Parse single-frame DM1 messages.
- Parse multi-frame DM1 messages using BAM (Broadcast Announce Message).
- Maintain a list of active faults, adding new faults and marking those that are inactive for a specified period.
- Emulate real-time processing based on timestamps in the log file.
- GUI display of active faults with dynamic updates.
- Adjustable fault timeout setting via GUI.

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
   - `PRINT_NEW_ACTIVE_DTCs`: Print new active DTCs.
   - `PRINT_REMOVED_DTCs`: Print removed DTCs.
3. Run the script.

## GUI Display

The GUI displays the following columns for each active fault:

- `SRC`: Source Address
- `SPN`: Suspect Parameter Number
- `FMI`: Failure Mode Identifier
- `OC`: Occurrence Count
- `MIL`: Malfunction Indicator Lamp status
- `RSL`: Red Stop Lamp status
- `AWL`: Amber Warning Lamp status
- `PL`: Protect Lamp status
- `Last Seen`: Timestamp of the last occurrence

### GUI Elements

- **Timestamp Display**: Shows the current emulated time in seconds.
- **Fault Timeout**: An entry field and button to adjust the fault timeout duration.

### Example GUI

To emulate the log processing time and manage the active faults list with GUI display:

```python
EMULATE_TIME = True  # Enable time emulation
DISPLAY_SCREEN = True  # Enable GUI display
fault_timeout = 10   # Set the timeout for removing inactive faults

# Call the function with the path to the log file
file_path = 'example_files/VWConstel2024_1.asc'
read_log_and_print_dtc(file_path)
```

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

### When `EMULATE_TIME` and `PRINT_ACTIVE_DTCs` is active:

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

To emulate the log processing time and manage the active faults list:

```python
EMULATE_TIME = True  # Enable time emulation
fault_timeout = 50   # Set the timeout for removing inactive faults

# Call the function with the path to the log file
file_path = 'example_files/VWConstel2024_1.asc'
read_log_and_print_dtc(file_path)
```

This will process the log file, parse the DTC messages, manage the active faults list, and print the results based on the specified print control variables.
