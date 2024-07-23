import re

# Variáveis de controle para impressão
PRINT_TP_CT = False
PRINT_TP_DT = False
PRINT_TP_CONCAT = False
PRINT_INCORRET_ORDER = False
PRINT_J1939TP_FECAp = False
PRINT_DM1_LINE = True
PRINT_DM1_PARAMS = True


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

# Verifica se o segundo byte do identificador CAN é EC
def is_bam_message_id(message_id):
    message_id = message_id.zfill(8)  # Garante que o identificador tenha 8 caracteres
    return message_id[2:4] == 'EC'

# Verifica se o segundo byte do identificador CAN é EB
def is_tp_dt_message_id(message_id):
    message_id = message_id.zfill(8)  # Garante que o identificador tenha 8 caracteres
    return message_id[2:4] == 'EB'

# Verifica se o segundo e terceiro bytes do identificador CAN é FECA
def is_dm1_message_id(message_id):
    message_id = message_id.zfill(8)  # Garante que o identificador tenha 8 caracteres
    return message_id[2:6] == 'FECA'

def bytes_to_binary_string(byte_list):
    # Converte cada byte para uma string de 8 bits binários e junta todos em uma string
    binary_string = ''.join(format(byte, '08b') for byte in byte_list)
    return binary_string


# Função para analisar a mensagem DM1
def parse_dm1_message(data_bytes):
    #print(data_bytes)
    # binary_str = bytes_to_binary_string(data_bytes)
    # print(binary_str)
    # spn_start = 2*8
    # spn1 = binary_str[spn_start: spn_start + 8]
    # #print('SPN 1', spn1)
    # spn2 = binary_str[spn_start + 8: spn_start + 16]
    # #print('SPN 2', spn2)
    # spn3 = binary_str[spn_start + 16: spn_start + 16 + 3]
    # # print('SPN 3', spn3)
    # spn = spn3 + spn2 + spn1
    # print('SPN', spn, int(spn,2), hex(int(spn, 2)))
    # start = (4*8)+3
    # aux = binary_str[start : start+5]
    # print('FMI_AUX', aux, int(aux, 2))
    # start = (5*8)+1
    # aux = binary_str[start : start+7]
    # print('OC_AUX', aux, int(aux, 2))

    
    dtc_params = []
    for i in range(0, len(data_bytes), 8):
        #byte1:2    
        mil = (data_bytes[i] >> 6) & 0x03 # Malfunction Indicator Lamp status
        #byte1:2
        rsl = (data_bytes[i] >> 4) & 0x03 # Red Stop Lamp status
        #byte1:2
        awl = (data_bytes[i] >> 2) & 0x03 # Amber Warning Lamp status
        #byte1:2
        pl = data_bytes[i] & 0x03 # Protect Lamp status
        #byte2
        rfu = data_bytes[i+1] # reserved
        # (byte5:3)<<16 | (byte4:8) << 8 | byte3
        spn = (((data_bytes[i+4] >> 5) & 0x7) << 16) | ((data_bytes[i+3] << 8) & 0xFF00) | data_bytes[i+2]
        # print(spn, hex(spn))
        #byte5:5
        fmi = data_bytes[i+4] & 0x1F #
        #byte6:1
        cm = (data_bytes[i+5] >> 7) & 0x01 # Conversion Method
        #byte6:7
        oc = data_bytes[i+5] & 0x7F # Occurence Counter 
        dtc_params.append((mil, rsl, awl, pl, spn, fmi, cm, oc))
    return dtc_params



# Função principal para ler o arquivo de log e imprimir DTCs de frames individuas ou de frames TP.CT(BAM) e TP.DT
def read_log_and_print_dtc(file_path):
    current_bams = []  # Lista para armazenar mensagens BAM atuais

    with open(file_path, 'r') as file:
        for line in file:
            if 'Rx' in line:
                # O dado que foi dividido em diversos pacotes, é concatenado e fornecido pelo próprio log com o nome 'J1939TP'
                # printamos apenas para comparar com nossa logica de concatenacao
                if 'J1939TP FECAp' in line:  
                    if PRINT_J1939TP_FECAp:
                        print(line.strip())
                
                parts = line.split()
                message_id = parts[2]

                if(is_dm1_message_id(message_id)):
                    if PRINT_DM1_LINE:
                        print(line.strip())
                    if PRINT_DM1_PARAMS:
                        # Analisar e imprimir detalhes da mensagem DM1
                        data_bytes = [int(b, 16) for b in parts[6:14]]

                        # Conversion Method
                        cm = (data_bytes[5] >> 7) & 0x01 

                        #Apenas parsea se Metodo de Conversao for 1, se nao consideramos metodo como desconhecido
                        if(cm == 1):
                            dtc_params = parse_dm1_message(data_bytes)
                            for p in dtc_params:
                                print(f"DM1 -> MIL: {p[0]}, RSL: {p[1]}, AWL: {p[2]}, PL: {p[3]}, SPN: 0x{format(p[4], 'X')} ({p[4]}), FMI: {p[5]}, CM: {p[6]}, OC: {p[7]}")
                
                elif is_bam_message_id(message_id):  # Identifica mensagem BAM
                    result = parse_tp_ct_message(line)
                    if result:
                        timestamp, message_id, total_size, num_packets, pgn = result

                        # Se nao for PGN de DTC, ignora
                        if pgn != 65226:
                            continue

                        # Substitui 'EC' por 'EB' para obter o message_id_tp
                        message_id_tp = message_id.replace('EC', 'EB', 1)

                        # Remove BAMs anteriores com o mesmo message_id
                        for bam in current_bams:
                            if bam['message_id'] == message_id:
                                current_bams.remove(bam)

                        # Adiciona a nova mensagem BAM à lista
                        current_bams.append({
                            'timestamp': timestamp,
                            'message_id': message_id,
                            'message_id_tp': message_id_tp,
                            'total_size': total_size,
                            'num_packets': num_packets,
                            'pgn': pgn,
                            'packets': []
                        })
                        if PRINT_TP_CT:
                            print(f"TP.CT -> Time: {timestamp}, ID: {message_id}, Size: {total_size} bytes, Number of Packets: {num_packets}, PGN: {pgn:#X}")
                elif is_tp_dt_message_id(message_id):  # Identifica mensagem TP.DT
                    result = parse_tp_dt_message(line)
                    if result:
                        timestamp, message_id, packet_number, data = result
                        if PRINT_TP_DT:
                            print(f"TP.DT ->  Time: {timestamp}, ID: {message_id}, Packet Number: {packet_number}, Data: {' '.join(data)}")

                        # Verifica se todos os pacotes foram recebidos
                        for bam in current_bams:
                            if bam['message_id_tp'] == message_id:
                                if packet_number != (len(bam['packets']) + 1):
                                    if PRINT_INCORRET_ORDER:
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
                                    # Limita o tamanho dos dados combinados
                                    combined_data = combined_data[:bam['total_size']]
                                    if PRINT_TP_CONCAT:
                                        print(f"J1939TP -> Time: {bam['timestamp']}, ID: {bam['message_id']}, Size: {bam['total_size']}, Data: {' '.join(combined_data)}")
                                    # Remove a BAM processada da lista
                                    current_bams.remove(bam)
                                    break

# Chamar a função com o caminho para o arquivo de log
file_path = 'example_files/test.asc'
# file_path = 'example_files/VWConstel2024_1.asc'
read_log_and_print_dtc(file_path)
