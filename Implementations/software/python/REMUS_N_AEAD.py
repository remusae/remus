
# REMUS-N Python Implementation

# Copyright 2018:
#     Thomas Peyrin <thomas.peyrin@gmail.com>

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.

from SKINNY import *
import math

# ####################################################################
# # REMUS-N
# ####################################################################


# REMUS-N1
SKINNY_VERSION = 3
N_LENGTH = 16
B_LENGTH = 16
COUNTER_LENGTH = 16
ICE = 1
MEMBER_MASK = 0

# REMUS-N2
# SKINNY_VERSION = 3
# N_LENGTH = 16
# B_LENGTH = 16
# COUNTER_LENGTH = 16
# ICE = 2
# MEMBER_MASK = 64

# REMUS-N3
# SKINNY_VERSION = 1
# N_LENGTH = 12
# B_LENGTH = 8
# COUNTER_LENGTH = 15
# ICE = 3
# MEMBER_MASK = 128



def increase_counter(counter):
    if counter[COUNTER_LENGTH - 1] & 0x80 != 0:
        if COUNTER_LENGTH == 16:
            mask = 0x87
        elif COUNTER_LENGTH == 15:
            mask = 0x1b
    else:
        mask = 0
    for i in reversed(range(1, COUNTER_LENGTH)):
        counter[i] = ((counter[i] << 1) & 0xfe) ^ (counter[i - 1] >> 7)
    counter[0] = ((counter[0] << 1) & 0xfe) ^ mask

    return counter


def parse(L_in,x): 
    L_out = []
    cursor = 0
    while len(L_in) - cursor >= x:
       L_out.extend([L_in[cursor:cursor+x]])
       cursor = cursor + x 
    if len(L_in) - cursor > 0:
       L_out.extend([L_in[cursor:]])
    if L_in == []:
        L_out = [[]]
    L_out.insert(0,[])
    return L_out


def pad(x, pad_length):
    if len(x) == 0:
        return [0] * pad_length
    if len(x) == pad_length:
        return x[:]
    y = x[:]
    for _ in range(pad_length - len(x) - 1):
        y.append(0)
    y.append(len(x))
    return y


def G(A):
    return [(x >> 1) ^ ((x ^ x << 7) & 0x80) for x in A]


def rho(S, M):
    G_S = G(S)
    C = [M[i] ^ G_S[i] for i in range(B_LENGTH)]
    S_prime = [S[i] ^ M[i] for i in range(B_LENGTH)]
    return S_prime, C


def rho_inv(S, C):
    G_S = G(S)
    M = [C[i] ^ G_S[i] for i in range(B_LENGTH)]
    S_prime = [S[i] ^ M[i] for i in range(B_LENGTH)]
    return S_prime, M


def KDF_ICE(N, K):
    if ICE == 1: 
        L = G(skinny_enc(N,K,SKINNY_VERSION))
        V = [0]*B_LENGTH
    elif ICE == 2:
        L_prime = skinny_enc(N,K,SKINNY_VERSION)        
        K_prime = K[:]
        K_prime[15] = K_prime[15] ^ 1
        V_prime = skinny_enc(L_prime,K_prime,SKINNY_VERSION)
        L = G(L_prime)
        V = G(V_prime)
    elif ICE == 3:
        N_prime = N[:] + [0]*4
        L = [K[i] ^ N_prime[i] for i in range(16)]
        V = [0] * B_LENGTH
    return L, V

# function that implements the AE encryption
def crypto_aead_encrypt(M, A, N, K):
    L, V = KDF_ICE(N,K)
    S = [0] * B_LENGTH

    A_parsed = parse(A,B_LENGTH)
    a = len(A_parsed)-1
    if len(A_parsed[a]) < B_LENGTH: wa = 13 
    else: wa = 12
    A_parsed[a] = pad(A_parsed[a],B_LENGTH)

    M_parsed = parse(M,B_LENGTH)
    m = len(M_parsed)-1
    if len(M_parsed[m]) < B_LENGTH: wm = 11 
    else: wm = 10
    z = len(M_parsed[m])
    M_parsed[m] = pad(M_parsed[m],B_LENGTH)

    for i in range(1,a+1):
        S, _ = rho(S, A_parsed[i])
        L = increase_counter(L)
        if ICE!=3: V = increase_counter(V)
        tweak = L[:]
        if i<a: tweak[15] = tweak[15] ^ MEMBER_MASK ^ 4
        else: tweak[15] = tweak[15] ^ MEMBER_MASK ^ wa
        S = [S[j] ^ V[j] for j in range(B_LENGTH)]
        S = skinny_enc(S, tweak, SKINNY_VERSION)
        S = [S[j] ^ V[j] for j in range(B_LENGTH)]

    C = []
    for i in range(1,m+1):
        S, x = rho(S, M_parsed[i])
        L = increase_counter(L)
        if ICE!=3: V = increase_counter(V)
        tweak = L[:]
        if i<m: tweak[15] = tweak[15] ^ MEMBER_MASK ^ 2
        else: tweak[15] = tweak[15] ^ MEMBER_MASK ^ wm
        S = [S[j] ^ V[j] for j in range(B_LENGTH)]
        S = skinny_enc(S, tweak, SKINNY_VERSION)
        S = [S[j] ^ V[j] for j in range(B_LENGTH)]
        if i<m: C.extend(x)
        else: C.extend(x[:z])

    _, T = rho(S, [0] * B_LENGTH)
    C.extend(T)
    return C


# function that implements the AE decryption
def crypto_aead_decrypt(C, A, N, K):
    T = C[-B_LENGTH:]
    C[-B_LENGTH:] = []
    L, V = KDF_ICE(N,K)
    S = [0] * B_LENGTH

    A_parsed = parse(A,B_LENGTH)
    a = len(A_parsed)-1
    if len(A_parsed[a]) < B_LENGTH: wa = 13 
    else: wa = 12
    A_parsed[a] = pad(A_parsed[a],B_LENGTH)

    C_parsed = parse(C,B_LENGTH)
    c = len(C_parsed)-1
    if len(C_parsed[c]) < B_LENGTH: wc = 11 
    else: wc = 10
    z = len(C_parsed[c])
    C_parsed[c] = pad(C_parsed[c],B_LENGTH)

    for i in range(1,a+1):
        S, _ = rho(S, A_parsed[i])
        L = increase_counter(L)
        if ICE!=3: V = increase_counter(V)
        tweak = L[:]
        if i<a: tweak[15] = tweak[15] ^ MEMBER_MASK ^ 4
        else: tweak[15] = tweak[15] ^ MEMBER_MASK ^ wa
        S = [S[j] ^ V[j] for j in range(B_LENGTH)]
        S = skinny_enc(S, tweak, SKINNY_VERSION)
        S = [S[j] ^ V[j] for j in range(B_LENGTH)]

    M = []
    for i in range(1,c+1):
        if i==c:
            S_tilde = G(S[:])    
            S_tilde = [0]*z + S_tilde[z-B_LENGTH:]
            C_parsed[c] = [C_parsed[c][j] ^ S_tilde[j] for j in range(B_LENGTH)]
        S, x = rho_inv(S, C_parsed[i])
        L = increase_counter(L)
        if ICE!=3: V = increase_counter(V)
        tweak = L[:]
        if i<c: tweak[15] = tweak[15] ^ MEMBER_MASK ^ 2
        else: tweak[15] = tweak[15] ^ MEMBER_MASK ^ wc
        S = [S[j] ^ V[j] for j in range(B_LENGTH)]
        S = skinny_enc(S, tweak, SKINNY_VERSION)
        S = [S[j] ^ V[j] for j in range(B_LENGTH)]
        if i<c: M.extend(x)
        else: M.extend(x[:z])

    _, T_computed = rho(S, [0] * B_LENGTH)
    compare = 0
    for i in range(B_LENGTH):
        compare |= (T[i] ^ T_computed[i])

    if compare != 0:
        return -1, []
    else:
        return 0, M
