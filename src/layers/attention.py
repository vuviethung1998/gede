import torch
import torch.nn as nn
import torch.nn.functional as F


class AttentionLSTM(nn.Module):
    def __init__(self, input_size, hidden_size, output_size, seq_len, drop_prob=0.5):
        super(AttentionLSTM, self).__init__()
        self.hidden_size = hidden_size
        self.input_size = input_size
        self.drop_prob = drop_prob
        self.seq_len = seq_len

        self.lstm1 = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.lstm2 = nn.LSTM(hidden_size, hidden_size, batch_first=True)
        self.embedding = nn.Linear(self.input_size, self.hidden_size)
        self.attn = nn.Linear(self.hidden_size * 2, self.seq_len)
        self.attn_combine = nn.Linear(self.hidden_size * 2, self.hidden_size)
        self.dropout = nn.Dropout(self.drop_prob)
        self.lstm3 = nn.LSTM(self.hidden_size, self.hidden_size, batch_first=True)
        self.bn_1 = nn.BatchNorm1d(self.hidden_size)
        self.mlp_1 = nn.Linear(self.hidden_size, output_size)
        self.act_1 = nn.ReLU()
        self.mlp_2 = nn.Linear(output_size, output_size)

    def forward(self, inputs):
        transposed_inputs = torch.transpose(inputs, 0, 1)
        # for i in range(transposed_inputs.shape[0]):
        #     print(transposed_inputs[i])
        output, h = self.lstm1(transposed_inputs)
        enc_output, (h_s, c_s) = self.lstm2(output, h)

        # Dùng torch zeros để khởi tạo input cũng được. Hoặc dùng time step trước đó là inputs[:, -1, :]
        # embedded = self.embedding(torch.zeros(inputs.size(0), 1, inputs.size(2)))
        x = transposed_inputs[:, -1:, :]
        # for i in range(x.shape[0]):
        #     print(x[i])
        embedded = self.embedding(transposed_inputs[:, -1:, :])
        embedded = self.dropout(embedded)
        # print(f"Output embedded {embedded}")
        attn_weights = F.softmax(
            self.attn(torch.cat((embedded, h_s[-1].unsqueeze(1)), 2)), dim=2
        )
        # print(f"attention_weight {attn_weights}")
        attn_applied = torch.bmm(attn_weights, enc_output)
        output = torch.cat((embedded, attn_applied), 2)
        output = self.attn_combine(output)
        output = F.relu(output)
        output, _ = self.lstm3(output, (h_s, c_s))
        output = output[:, -1, :]
        output = self.bn_1(
            output
        )  # batch norm cần nhiều hơn 1 giá trị. (batch_size != 1)
        output = self.dropout(output)
        output = self.mlp_1(output)
        output = F.relu(output)
        output = self.mlp_2(output)
        return output

import math

class DotProductAttention(nn.Module):
    def __init__(self):
        super().__init__()
        self.softmax = nn.Softmax(dim=-1)

    def forward(self, key, query, mask=None):
        """_summary_

        Args:
            key (_type_): tensor([1,n_station,d_dim])
            query (_type_): tensor([1,n_station,d_dim])
            mask (_type_, optional): _description_. Defaults to None.

        Returns:
            _type_: _description_
        """

        n_station = key.shape[1]
        query = query.unsqueeze(1)
        score = torch.bmm(query, key.transpose(1, 2))
        if mask is not None:
            mask = mask.squeeze()
            score = score.masked_fill(mask == 0, -math.inf)
        attn = self.softmax(score.view(-1, n_station))
        return attn

class GeneralAttention(nn.Module):
    def __init__(self,d_dim):
        super().__init__()
        self.weight_attention = nn.Linear(d_dim, d_dim)
        self.softmax = nn.Softmax(dim=-1)

    def forward(self, key, query):
        n_station = key.shape[1]
        query = query.unsqueeze(1)
        attn = self.weight_attention(query)
        score = torch.bmm(attn, key.transpose(1, 2))
        attn_score = self.softmax(score.view(-1, n_station))
        return attn_score
# if __name__ == "__main__":
#   atten_layer = AttentionLSTM(1,60,120,12,0.1)
#   print(atten_layer(torch.rand(12,27,1)).shape)
