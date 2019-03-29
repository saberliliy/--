from keras.models import Model
from keras.layers import Input, LSTM, Dense
from keras import callbacks
import numpy as np
import  re
from keras import layers
from keras.layers import Input, Dense, Activation, ZeroPadding2D, BatchNormalization, Flatten, Conv2D,Conv1D
from keras.layers import AveragePooling2D, MaxPooling2D, Dropout, GlobalMaxPooling2D, GlobalAveragePooling2D
from keras.models import Model
from keras.preprocessing import image
from keras.utils import layer_utils
from keras.utils.data_utils import get_file
from keras.applications.imagenet_utils import preprocess_input
from keras.utils.vis_utils import model_to_dot
from keras.utils import plot_model

batch_size=64
epochs=1
latent_dim=256                                              #lstm 神经元的个数
num_samples=10000
data_path="./data.txt"
input_texts = []
target_texts = []
input_characters = set()
target_characters = set()

with open(data_path, 'r', encoding='utf-8') as f:
    lines = f.read().split('\n')
for line in lines[:min(num_samples,len(lines)-1)]:
    input_text,target_text=line.split("\t")
    target_text="\t"+target_text+"\n"
    input_texts.append(input_text)
    target_texts.append(target_text)
    for char in input_text:                            #采用字符的结构
        if char not in input_characters:
            input_characters.add(char)
    for char  in target_text:
        if char not in target_characters:
            target_characters.add(char)
input_characters = sorted(list(input_characters))
target_characters = sorted(list(target_characters))
num_encoder_tokens = len(input_characters)
num_decoder_tokens = len(target_characters)
max_encoder_seq_length = max([ len(txt) for txt in input_texts])
max_decoder_seq_length = max([ len(txt) for txt in target_texts])
print(len(input_characters))
print(max_encoder_seq_length)
input_token_index = dict( [(char, i)for i, char in enumerate(input_characters)] )
target_token_index = dict( [(char, i) for i, char in enumerate(target_characters)] )

encoder_input_data = np.zeros((len(input_texts), max_encoder_seq_length, num_encoder_tokens), dtype=np.float32)
decoder_input_data = np.zeros((len(input_texts), max_decoder_seq_length, num_decoder_tokens), dtype=np.float32)
decoder_target_data = np.zeros((len(input_texts), max_decoder_seq_length, num_decoder_tokens), dtype=np.float32)

for i, (input_text, target_text) in enumerate(zip(input_texts, target_texts)):
    for t, char in enumerate(input_text):
        encoder_input_data[i, t, input_token_index[char]] = 1.0
    for t, char in enumerate(target_text):
        decoder_input_data[i, t, target_token_index[char]] = 1.0
        if t > 0:
            decoder_target_data[i, t - 1, target_token_index[char]] = 1.0
X_input = Input(shape=(max_encoder_seq_length,num_encoder_tokens))
X = Conv1D(1, 3, strides=1, name='conv0',padding="same")(X_input)
# encoder_inputs = Input(shape=(None, num_encoder_tokens))
encoder = LSTM(latent_dim, return_state=True)
encoder_outpus, state_h, state_c = encoder(X)
encoder_state = [state_h, state_c]

decoder_inputs = Input(shape=(None, num_decoder_tokens))
decoder_lstm = LSTM(latent_dim, return_sequences=True, return_state=True)
decoder_outputs, _, _ = decoder_lstm(decoder_inputs, initial_state=encoder_state)
decoder_dense = Dense(num_decoder_tokens, activation='softmax')
decoder_outputs = decoder_dense(decoder_outputs)

model = Model([X_input, decoder_inputs], decoder_outputs)
model.compile(optimizer='rmsprop', loss='categorical_crossentropy')
model.fit([encoder_input_data, decoder_input_data], decoder_target_data,
          batch_size=batch_size,
          epochs = epochs,
          validation_split=0.2)
model.save('s2s_2.h5')
encoder_model = Model(X_input, encoder_state)

decoder_state_input_h = Input(shape=(latent_dim,))
decoder_state_input_c = Input(shape=(latent_dim,))
decoder_states_inputs = [decoder_state_input_h, decoder_state_input_c]

# 得到解码器的输出以及中间状态
decoder_outputs, state_h, state_c = decoder_lstm(decoder_inputs, initial_state=decoder_states_inputs)
decoder_states = [state_h, state_c]
decoder_outputs = decoder_dense(decoder_outputs)

decoder_model = Model([decoder_inputs] + decoder_states_inputs, [decoder_outputs]+decoder_states)

reverse_input_char_index = dict([(i, char) for char, i in input_token_index.items()])
reverse_target_char_index = dict([(i, char) for char, i in target_token_index.items()])



def decode_sequence(input_seq):

    states_value = encoder_model.predict(input_seq)

    target_seq = np.zeros((1, 1, num_decoder_tokens))

    target_seq[0, 0, target_token_index['\t']] = 1.

    stop_condition = False
    decoded_sentence = ''

    while not stop_condition:
        output_tokens, h, c = decoder_model.predict([target_seq] + states_value)

        sampled_token_index = np.argmax(output_tokens[0, -1, :])
        sampled_char = reverse_target_char_index[sampled_token_index]
        decoded_sentence += sampled_char

        if sampled_char == '\n' or len(decoded_sentence) > max_decoder_seq_length :
            stop_condition = True

        target_seq = np.zeros((1, 1, num_decoder_tokens))
        target_seq[0, 0, sampled_token_index] = 1.


        states_value = [h, c]

    return decoded_sentence


for seq_index in range(1000, 1100):

    input_seq = encoder_input_data[seq_index:seq_index+1]
    decoded_sentence = decode_sequence(input_seq)

    print('-')
    print('Input sentence:', input_texts[seq_index])
    print('Decoded sentence:', decoded_sentence)
