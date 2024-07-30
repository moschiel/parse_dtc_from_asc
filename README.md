
# parse_dtc_from_asc

**Description**: Parse J1939 Diagnostics Trouble Code (DTC) from CANalyzer ASC logging file.

<!-- ![image](https://github.com/user-attachments/assets/0cf920b0-2f3a-4ac5-8aae-b8e9b04ca8ec) -->
![image](https://github.com/user-attachments/assets/b5418880-89e9-47e7-ab4d-7c8e174c6121)



## Overview

This script processes J1939 Diagnostic Trouble Code (DTC) messages from a CANalyzer ASC logging file, specifically focusing on messages with PGN 0xFECA (DM1). It can handle both single-frame and multi-frame (BAM) messages and maintains a list of active faults, removing them if they are not seen for a specified period (debounce inactive). The GUI provides a real-time display of active faults, their status, and an adjustable timeout setting.

## Features

- Parse single-frame DM1 messages.
- Parse multi-frame DM1 messages using BAM (Broadcast Announce Message).
- Maintain a list of active faults, adding new faults and marking those that are inactive for a specified period (debounce inactive).
- Emulate real-time processing based on timestamps in the log file.
- GUI display of active faults (white) , inactive faults (gray), and candidate faults (white), with dynamic updates.
- GUI adjustable debounce time setting for a fault to become 'active' or 'inactive' .

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
   - `PRINT_REMOVED_ACTIVE_DTCs`: Print removed DTCs that was active before.
   - `PRINT_REMOVED_CANDIDATE_DTCs`: Print removed DTCs that was a candidate before.
3. Run the script.

## GUI Display

The GUI displays the following columns for each active fault:

- `SRC`: Source Address
- `SPN`: Suspect Parameter Number
- `FMI`: Failure Mode Identifier
- 'CM': SPN Conversion Method
- `OC`: Occurrence Count
- `MIL`: Malfunction Indicator Lamp status
- `RSL`: Red Stop Lamp status
- `AWL`: Amber Warning Lamp status
- `PL`: Protect Lamp status
- `Last Seen`: Timestamp of the last occurrence

### GUI Elements

- **Timestamp Display**: Shows the current emulated time in seconds.
- **Debounce Inactive Fault**: An entry field to adjust the debounce duration for a fault to change from 'active' to 'inactive'.
- **Debounce Active Fault**: An entry field to adjust the debounce active window for a fault to change from 'candidate' to 'active'.
- **Debounce Active Count**: An entry field to adjust how many times a fault code must be read in order to change from 'candidate' to 'active' within the debounce active window.

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
