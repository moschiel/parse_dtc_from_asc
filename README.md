
# Parse DTC from CANalyzer ASC File

Parse J1939 Diagnostics Trouble Code (DTC) from CANalyzer ASC logging file

## Overview

This project provides a Python script to parse J1939 Diagnostic Trouble Codes (DTC) from CANalyzer ASC logging files. The script specifically targets messages with the PGN 0xFECA, which are used to transmit Diagnostic Message 1 (DM1) data. It also handles the concatenation of multi-packet messages using the Transport Protocol (TP).

## Features

- Parses single-frame DM1 messages (PGN 0xFECA).
- Concatenates and parses multi-frame DM1 messages transmitted using BAM (Broadcast Announce Message) and TP.DT (Data Transfer) messages.
- Provides detailed output of parsed DM1 messages, including status of various indicator lamps and detailed DTC information.
- Emulates the time between log entries to simulate real-time parsing.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/parse_dtc_from_asc.git
   cd parse_dtc_from_asc
   ```

2. Ensure you have Python 3.x installed on your system.

## Usage

1. Place your CANalyzer ASC log file in the `example_files` directory.
2. Edit the `file_path` variable in the script to point to your log file.
3. Run the script:
   ```bash
   python parse_dtc_from_asc.py
   ```

## Configuration

- `PRINT_DM1_SINGLE_FRAME`: Controls printing of single-frame DM1 messages.
- `PRINT_TP_CT`: Controls printing of TP.CT messages.
- `PRINT_TP_DT`: Controls printing of TP.DT messages.
- `PRINT_J1939TP_FECAp`: Controls printing of concatenated J1939TP FECA messages.
- `PRINT_TP_DM1_MULTI_FRAME`: Controls printing of multi-frame DM1 messages.
- `PRINT_INCORRET_ORDER`: Controls printing of incorrect packet order messages.
- `PRINT_DM1_PARSED`: Controls printing of parsed DM1 messages.
- `EMULATE_TIME`: Controls whether to emulate the time between log entries.

## Output Format

When only `PRINT_DM1_PARSED` is set to `True`, the output will display parsed DM1 messages in the following format:

```
DM1 -> Time: [timestamp], SRC: 0x[src] ([src_decimal]), MIL: [mil_status], RSL: [rsl_status], AWL: [awl_status], PL: [pl_status]
        DTC[1] -> SPN: 0x[spn_hex] ([spn_decimal]), FMI: [fmi], CM: [cm], OC: [oc]
        DTC[2] -> SPN: 0x[spn_hex] ([spn_decimal]), FMI: [fmi], CM: [cm], OC: [oc]
        ...
```

### Example

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
DM1 -> Time: 111.796362, SRC: 0x27 (39), MIL: 0, RSL: 0, AWL: 1, PL: 0
        DTC[1] -> SPN: 0x7EE22 (519714), FMI: 3, CM: 1, OC: 1
        DTC[2] -> SPN: 0x1EE52 (126546), FMI: 3, CM: 1, OC: 1
        DTC[3] -> SPN: 0xEE52 (61010), FMI: 3, CM: 1, OC: 1
        DTC[4] -> SPN: 0x3F442 (259138), FMI: 0, CM: 1, OC: 1
```

## Contributing

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Commit your changes (`git commit -m 'Add new feature'`).
4. Push to the branch (`git push origin feature-branch`).
5. Create a new Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.