import re

# Função para analisar a mensagem BAM TP:CT
def parse_tp_ct_message(line):
    parts = line.split()
    timestamp = parts[0]
    message_id = parts[2]
    data_bytes = parts[6:14]

    control_byte = data_bytes[0]

    if control_byte == '20':  # Verifica se é uma mensagem BAM
        # inverte a ordem dos bytes para o total size
        total_size = int(data_bytes[2] + data_bytes[1], 16)
        num_packets = int(data_bytes[3], 16)
        reserved = data_bytes[4]
        # inverte a ordem dos bytes para o PGN
        pgn = int(data_bytes[7] + data_bytes[6] + data_bytes[5], 16)
        return timestamp, message_id, total_size, num_packets, pgn
    return None

# Função para analisar a mensagem BAM TP.DT
def parse_tp_dt_message(line):
    parts = line.split()
    timestamp = parts[0]
    message_id = parts[2]
    data_bytes = parts[6:14]

    packet_number = int(data_bytes[0], 16)
    data = data_bytes[1:8]
    return timestamp, message_id, packet_number, data

# Função principal para ler o arquivo de log e imprimir as mensagens BAM e TP.DT
def read_log_and_print_bam_tp(file_path):
    current_bams = []  # Lista para armazenar mensagens BAM atuais

    with open(file_path, 'r') as file:
        for line in file:
            if 'Rx' in line:
                if 'J1939TP' in line: # O dado que foi divido em diversos pacote, é contatenado e fornececido pelo proprio log com o nome 'J1939TP'
                    print(line)
                if '18EC' in line:  # Identifica mensagem BAM
                    result = parse_tp_ct_message(line)
                    if result:
                        timestamp, message_id, total_size, num_packets, pgn = result

                        posicao = 3
                        message_id_tp = message_id[:posicao] + 'B' + message_id[posicao + 1:]

                        for bam in current_bams:
                            if bam['message_id'] == message_id:
                                current_bams.remove(bam)

                        current_bams.append({
                            'timestamp': timestamp,
                            'message_id': message_id,
                            'message_id_tp': message_id_tp, 
                            'total_size': total_size,
                            'num_packets': num_packets,
                            'pgn': pgn,
                            'packets': []
                        })
                        print(f"TP.CT ->  Timestamp: {timestamp}, Message ID: {message_id}, Total Size: {total_size} bytes, Number of Packets: {num_packets}, PGN: {pgn:#X}")
                elif '18EB' in line:  # Identifica mensagem TP.DT
                    result = parse_tp_dt_message(line)
                    if result:
                        timestamp, message_id, packet_number, data = result
                        print(f"TP.DT ->  Timestamp: {timestamp}, Message ID: {message_id}, Packet Number: {packet_number}, Data: {' '.join(data)}")

                        # Verifica se todos os pacotes foram recebidos
                        for bam in current_bams:
                            if bam['message_id_tp'] == message_id:

                                if(packet_number != (len(bam['packets']) + 1)):
                                    print('Ordem do pacote incorreta')
                                    current_bams.remove(bam)
                                    break

                                bam['packets'].append((packet_number, data))
                                if len(bam['packets']) == bam['num_packets']:
                                    # Ordena os pacotes pelo número do pacote
                                    bam['packets'].sort()
                                    combined_data = []
                                    for packet in bam['packets']:
                                        combined_data.extend(packet[1])
                                    print(f"***** J1939TP -> Timestamp: {bam['timestamp']}, Message ID: {bam['message_id']}, Size: {bam['total_size']}, Data: {' '.join(combined_data)}")
                                    # Remove a BAM processada da lista
                                    current_bams.remove(bam)
                                    break

# Chamar a função com o caminho para o arquivo de log
file_path = 'test.asc'
read_log_and_print_bam_tp(file_path)
