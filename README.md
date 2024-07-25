
# Parse DTC from ASC

Parse J1939 Diagnostics Trouble Code (DTC) from CANalyzer ASC logging file

## Overview

This project provides a Python script to parse J1939 Diagnostic Trouble Codes (DTC) from CANalyzer ASC logging files. The script specifically targets messages with the PGN 0xFECA, which are used to transmit Diagnostic Message 1 (DM1) data. It also handles the concatenation of multi-packet messages using the Transport Protocol (TP).

## Features

- Parses single-frame DM1 messages (PGN 0xFECA).
- Concatenates and parses multi-frame DM1 messages transmitted using BAM (Broadcast Announce Message) and TP.DT (Data Transfer) messages.
- Provides detailed output of parsed DM1 messages, including status of various indicator lamps and detailed DTC information.

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

## Code Structure

### Main Function

```python
def read_log_and_print_dtc(file_path):
    current_bams = []  # List to store current BAM messages
    with open(file_path, 'r') as file:
        for line in file:
            if 'Rx' in line:
                if 'J1939TP FECAp' in line:  
                    if PRINT_J1939TP_FECAp:
                        print(line.strip())
                parts = line.split()
                message_id = parts[2]
                src = message_id.zfill(8)[6:8]
                if(is_dm1_message_id(message_id)):
                    data_bytes = [int(b, 16) for b in parts[6:14]]
                    spn = (((data_bytes[4] >> 5) & 0x7) << 16) | ((data_bytes[3] << 8) & 0xFF00) | data_bytes[2]
                    if spn != 0:
                        if PRINT_DM1_SINGLE_FRAME:
                            print(line.strip())
                        timestamp = parts[0]
                        parse_dm1_message(timestamp, src, data_bytes)
                elif is_tp_cm_message_id(message_id):
                    result = parse_tp_ct_message(line)
                    if result:
                        timestamp, message_id, total_size, num_packets, pgn = result
                        if pgn != 65226:
                            continue
                        message_id_tp_ct = message_id.replace('EC', 'EB', 1)
                        for bam in current_bams:
                            if bam['message_id'] == message_id:
                                current_bams.remove(bam)
                        current_bams.append({
                            'timestamp': timestamp,
                            'message_id': message_id,
                            'message_id_tp_ct': message_id_tp_ct,
                            'total_size': total_size,
                            'num_packets': num_packets,
                            'pgn': pgn,
                            'packets': []
                        })
                        if PRINT_TP_CT:
                            print(f"TP.CT -> Time: {timestamp}, ID: {message_id}, Size: {total_size} bytes, Number of Packets: {num_packets}, PGN: {pgn:#X}")
                elif is_tp_dt_message_id(message_id):
                    result = parse_tp_dt_message(line)
                    if result:
                        timestamp, message_id, packet_number, data = result
                        if PRINT_TP_DT:
                            print(f"TP.DT ->  Time: {timestamp}, ID: {message_id}, Packet Number: {packet_number}, Data: {' '.join(data)}")
                        for bam in current_bams:
                            if bam['message_id_tp_ct'] == message_id:
                                if packet_number != (len(bam['packets']) + 1):
                                    if PRINT_INCORRET_ORDER:
                                        print('Packet Order is Incorrect')
                                    current_bams.remove(bam)
                                    break
                                bam['packets'].append((packet_number, data))
                                if len(bam['packets']) == bam['num_packets']:
                                    bam['packets'].sort()
                                    combined_data = []
                                    for packet in bam['packets']:
                                        combined_data.extend(packet[1])
                                    combined_data = combined_data[:bam['total_size']]
                                    if PRINT_TP_DM1_MULTI_FRAME:
                                        print(f"TP -> Time: {bam['timestamp']}, ID: {bam['message_id']}, Size: {bam['total_size']}, Data: {' '.join(combined_data)}")
                                    data_bytes = [int(b, 16) for b in combined_data]
                                    parse_dm1_message(timestamp, src, data_bytes)
                                    current_bams.remove(bam)
                                    break
```

### Helper Functions

- `parse_tp_ct_message(line)`: Parses BAM TP:CT messages.
- `parse_tp_dt_message(line)`: Parses BAM TP.DT messages.
- `is_tp_cm_message_id(message_id)`: Checks if the message ID indicates a TP.CM message.
- `is_tp_dt_message_id(message_id)`: Checks if the message ID indicates a TP.DT message.
- `is_dm1_message_id(message_id)`: Checks if the message ID indicates a DM1 message.
- `bytes_to_binary_string(byte_list)`: Converts a list of bytes to a binary string.
- `parse_dm1_message(time, src, data_bytes)`: Parses DM1 messages and prints DTC details.

## Contributing

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Commit your changes (`git commit -m 'Add new feature'`).
4. Push to the branch (`git push origin feature-branch`).
5. Create a new Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

For any inquiries, please contact [your-email@example.com](mailto:your-email@example.com).
