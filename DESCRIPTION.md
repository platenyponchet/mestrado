# Descrição do Experimento

Benchmark comparativo de cinco algoritmos de compressão lossy aplicados a séries temporais de consumo de energia elétrica. O objetivo é avaliar o trade-off entre taxa de compressão, qualidade de reconstrução, tempo de execução e uso de memória em diferentes condições de janelamento e alvo de compressão.

---

## 0. Fundamentação Teórica

### 0.1 Transformada Wavelet Discreta (DWT)

#### 0.1.1 Análise de Multirresolução

A Transformada Wavelet Discreta decompõe um sinal em componentes de diferentes escalas (resoluções) e posições temporais. A ideia central é a **análise de multirresolução (MRA)**, introduzida por Mallat (1989): o espaço dos sinais é hierarquicamente decomposto em subespaços de aproximação e detalhe.

Dado um sinal discreto `x[n]` de comprimento N, a DWT de um nível aplica dois filtros FIR em paralelo:

```
x[n] ──┬── h[n] (passa-baixa) ──→ ↓2 ──→ cA  (coeficientes de aproximação)
       └── g[n] (passa-alta)  ──→ ↓2 ──→ cD  (coeficientes de detalhe)
```

Onde `↓2` denota subamostragem por fator 2. Os filtros `h` e `g` são o **par de filtros da wavelet** e satisfazem a condição de conjugado em quadratura:

```
g[n] = (-1)^n · h[L-1-n]
```

sendo L o comprimento do filtro. Após a subamostragem, cada subband tem comprimento `⌈N/2⌉`.

#### 0.1.2 Decomposição em L Níveis

A decomposição multi-nível aplica o banco de filtros recursivamente sobre os coeficientes de aproximação:

```
Nível 1:  x       → cA1, cD1
Nível 2:  cA1     → cA2, cD2
Nível 3:  cA2     → cA3, cD3
...
Nível L:  cA(L-1) → cAL, cDL
```

O resultado final é o conjunto `{cAL, cDL, cD(L-1), ..., cD1}`, com comprimentos aproximados `{N/2^L, N/2^L, N/2^(L-1), ..., N/2}`. O número total de coeficientes é ≈ N (não há expansão para wavelets ortogonais).

Em forma matricial, a DWT ortogonal de nível 1 pode ser escrita como:

```
W = W · x
```

onde `W` é uma matriz ortogonal (W^T · W = I), o que garante que a energia total é preservada (Parseval):

```
||x||² = ||W||²  →  Σ x[n]² = Σ coeff²
```

#### 0.1.3 Famílias de Wavelets

A escolha da família afeta o formato dos filtros `h` e `g` e, portanto, a capacidade de representar diferentes padrões no sinal:

| Família | Suporte | Simetria | Momentos nulos | Característica |
|---------|---------|----------|----------------|----------------|
| `db4` | 7 (L=8) | Assimétrica | 4 | Suave, boa para sinais regulares |
| `sym4` | 7 (L=8) | Quase simétrica | 4 | Similar à db4, menos distorção de fase |
| `bior4.4` | 9/7 | Simétrica | 4/4 | Biortogonal; filtros de análise ≠ síntese |

**Momentos nulos** de ordem K significam que a wavelet é ortogonal a polinômios de grau até K-1. Na prática, isso indica que componentes polinomiais são capturados pelos coeficientes de aproximação e produzem coeficientes de detalhe próximos de zero — o que favorece a compressão.

#### 0.1.4 Hard Thresholding

Após a decomposição, a compressão é feita zerando os K coeficientes de menor magnitude. Para um orçamento de K coeficientes a manter, o **hard thresholding** define:

```
ĉ[i] = c[i],  se |c[i]| está entre os K maiores
ĉ[i] = 0,     caso contrário
```

O threshold λ que separa os K maiores pode ser definido como o K-ésimo maior valor em |c|:

```
λ = |c|_{(K)}   (K-ésima estatística de ordem decrescente)
```

O erro de reconstrução pelo teorema de Parseval é exatamente a energia dos coeficientes descartados:

```
||x - x̂||² = Σ_{i ∉ top-K} c[i]²
```

A DWT concentra a energia do sinal em poucos coeficientes de grande magnitude (propriedade de compactação de energia), especialmente para sinais suaves — por isso a compressão com poucos coeficientes produz boa reconstrução.

#### 0.1.5 Reconstrução (IDWT)

A reconstrução é feita pelo banco de síntese, que interpola (↑2) e filtra com os filtros duais `h̃` e `g̃`:

```
cAk, cDk  →  ↑2 + h̃  →  soma  →  cA(k-1)
              ↑2 + g̃  →
```

Para wavelets ortogonais: `h̃ = h`, `g̃ = g`. Para biortogonais (`bior4.4`): os filtros de síntese diferem dos de análise, mas a reconstrução perfeita ainda é garantida (sem coeficientes zerando).

---

### 0.2 Transformada Discreta do Cosseno (DCT)

#### 0.2.1 Definição Formal

A DCT-II (variante mais usada, referida simplesmente como "DCT") de um sinal `x[n]`, n = 0,...,N-1, é definida como:

```
X[k] = α[k] · Σ_{n=0}^{N-1} x[n] · cos( π·k·(2n+1) / (2N) )
```

onde o fator de normalização `α[k]` na forma **ortogonal** (`norm='ortho'` no SciPy) é:

```
α[0] = √(1/N)
α[k] = √(2/N),  k = 1, ..., N-1
```

Essa normalização garante que a matriz da DCT seja ortogonal: `C^T · C = I`.

A DCT inversa (IDCT-II) que recupera `x[n]` é:

```
x[n] = Σ_{k=0}^{N-1} α[k] · X[k] · cos( π·k·(2n+1) / (2N) )
```

#### 0.2.2 Interpretação como Base de Cossenos

Cada coeficiente `X[k]` é a projeção de `x` sobre o vetor base:

```
φ_k[n] = α[k] · cos( π·k·(2n+1) / (2N) )
```

Esses vetores formam uma base ortonormal de R^N. O coeficiente `X[0]` (k=0) é proporcional à média do sinal (componente DC). Para k crescente, `φ_k` oscila com frequência k/(2N) ciclos por amostra — da mais lenta (DC) à mais rápida (alternância amostra a amostra).

#### 0.2.3 Compactação de Energia

A DCT tem excelente **compactação de energia**: sinais suaves (com derivadas contínuas) concentram quase toda a sua energia nos primeiros coeficientes. Formalmente, a DCT é assintoticamente ótima para processos de Markov de primeira ordem (AR(1)), que são um modelo razoável para séries de consumo de energia.

Pelo teorema de Parseval para a DCT ortogonal:

```
||x||² = ||X||²  →  Σ_{n} x[n]² = Σ_{k} X[k]²
```

#### 0.2.4 Truncamento Espectral

A compressão consiste em manter apenas os K primeiros coeficientes (baixas frequências):

```
X̂[k] = X[k],  k = 0, 1, ..., K-1
X̂[k] = 0,     k = K, ..., N-1
```

O erro de reconstrução é a energia das altas frequências descartadas:

```
||x - x̂||² = Σ_{k=K}^{N-1} X[k]²
```

**Diferença em relação à Wavelet:** a DCT descarta as altas frequências globais do sinal inteiro, enquanto a Wavelet descarta coeficientes localizados no tempo E na frequência. Para sinais com transições abruptas (picos de carga), a Wavelet pode preservar melhor esses eventos porque os coeficientes de detalhe na escala certa são grandes em magnitude e serão mantidos. A DCT pode produzir **ringing** (oscilações artificiais) próximo a descontinuidades — o fenômeno de Gibbs.

#### 0.2.5 Relação com a DFT

A DCT é equivalente a uma DFT de comprimento 2N aplicada a uma extensão par do sinal. Por isso não há vazamento espectral (spectral leakage) nas bordas — a DCT assume implicitamente que o sinal é periodicamente extendido de forma simétrica, enquanto a DFT assume periodicidade circular que pode criar descontinuidades artificiais.

---

### 0.3 Algoritmo Ramer-Douglas-Peucker (RDP)

#### 0.3.1 Distância de Ponto à Reta

Dado um ponto `P = (x, y)` e uma reta definida pelos pontos `A = (x₁, y₁)` e `B = (x₂, y₂)`, a **distância perpendicular** de P à reta AB é:

```
d(P, AB) = |( y₂-y₁)·x - (x₂-x₁)·y + x₂·y₁ - y₂·x₁|
           ─────────────────────────────────────────────
                  √( (y₂-y₁)² + (x₂-x₁)² )
```

Quando A = B (segmento degenerado), adota-se `d = |y - y₁|` (distância vertical).

Para séries temporais, onde o eixo x é o tempo (uniformemente espaçado), a distância perpendicular leva em conta tanto o desvio vertical quanto a posição temporal do ponto.

#### 0.3.2 O Algoritmo

O RDP recebe uma sequência de pontos `P = [p₀, p₁, ..., p_{N-1}]` e um limiar `ε > 0`.

**Pseudocódigo:**

```
função RDP(P[i..j], ε):
    se j - i < 2:
        retorna P[i..j]          // segmento trivial

    d_max ← 0
    idx   ← i

    para k de i+1 até j-1:
        d ← distância_perpendicular(P[k], P[i], P[j])
        se d > d_max:
            d_max ← d
            idx   ← k

    se d_max > ε:
        esq   ← RDP(P[i..idx], ε)
        dir   ← RDP(P[idx..j], ε)
        retorna esq[:-1] + dir         // remove duplicata do ponto de junção

    senão:
        retorna [P[i], P[j]]           // descarta todos os intermediários
```

**Chamada inicial:** `RDP(P[0..N-1], ε)`

O resultado é um subconjunto de pontos originais que definem a curva simplificada. Os pontos inicial e final são sempre preservados.

#### 0.3.3 Propriedades

**Garantia de erro:** Para qualquer ponto `pₖ` descartado, sua distância perpendicular à reta entre os keypoints vizinhos que o delimitam é ≤ ε. Portanto, o erro máximo de reconstrução pontual (em distância perpendicular) é limitado por ε.

**Nota:** a garantia é em distância perpendicular, não em distância vertical pura — diferente do SDT, que garante erro vertical ≤ `error`.

**Complexidade:**
- Caso médio: O(N log N) — quando o ponto de maior distância divide o segmento de forma aproximadamente balanceada
- Pior caso: O(N²) — quando o ponto escolhido está sempre próximo a uma extremidade (ex.: série monotônica crescente com spike no início)
- Espaço (pilha de recursão): O(log N) esperado, O(N) no pior caso

**Offline vs. Online:** O RDP é um algoritmo **offline** — requer toda a série antes de começar. Isso o diferencia fundamentalmente do SDT e do ARC-SDT, que são online e processam ponto a ponto.

#### 0.3.4 Reconstrução por Interpolação Linear

Após a simplificação, os pontos descartados são reconstruídos por interpolação linear entre os keypoints adjacentes:

```
x̂(t) = x(t₀) + [ (t - t₀) / (t₁ - t₀) ] · (x(t₁) - x(t₀))
```

para t ∈ [t₀, t₁], onde t₀ e t₁ são timestamps de keypoints consecutivos.

O erro de reconstrução vertical em um ponto descartado `pₖ = (tₖ, xₖ)` entre keypoints `(t₀, x₀)` e `(t₁, x₁)` é:

```
eₖ = xₖ - x̂(tₖ) = xₖ - x₀ - [ (tₖ-t₀)/(t₁-t₀) ] · (x₁-x₀)
```

que é a diferença vertical entre o ponto real e a reta interpolada — geometricamente relacionada (mas não igual) à distância perpendicular usada no critério de simplificação.

---

## 1. Compressores

### 1.1 Wavelet (DWT)

**Princípio:** Representa o sinal no domínio tempo-frequência via Transformada Wavelet Discreta. Sinais de energia elétrica têm estrutura multirresolução natural — variações lentas (tendência diária) e variações rápidas (picos de carga) — que a wavelet captura em diferentes escalas. A compressão descarta os coeficientes de menor magnitude, que correspondem a detalhes de baixa energia.

**Pipeline:**
1. Normaliza a série para `[0, 1]` (`float32`)
2. Aplica `pywt.wavedec` com família wavelet escolhida e N níveis de decomposição
3. Converte todos os coeficientes para um array flat (`coeffs_to_array`)
4. Calcula o orçamento K: quantos coeficientes cabem no tamanho-alvo (considerando overhead de metadados e custo de 8 bytes por coeficiente — 4 para o valor + 4 para o índice original)
5. Mantém exatamente os K maiores em magnitude via `np.argpartition` (hard thresholding)
6. Reconstrói com `waverec` e reverte a normalização

**Parâmetros:**
| Parâmetro | Efeito |
|-----------|--------|
| `wavelet` | Família wavelet: `db4` (suave, boa para tendências), `bior4.4` (biortogonal, boa simetria), `sym4` (quase simétrica) |
| `level` | Profundidade da decomposição. Mais níveis → maior separação de escalas, mas requer série suficientemente longa |
| `cr` | % de redução alvo. Controla K diretamente via orçamento de bytes |

**Custo de transmissão:** 8 bytes por coeficiente (valor + índice), pois os coeficientes mantidos são espalhados pelo array — precisam de endereçamento explícito.

**Famílias testadas no experimento:** `db4`, `bior4.4`, `sym4` (wavelet-haar excluída das combinações padrão).

---

### 1.2 DCT (Transformada Discreta do Cosseno)

**Princípio:** Representa o sinal como soma de cossenos em diferentes frequências. Séries de consumo diário têm forte componente de baixa frequência (ciclo diurno). A compressão descarta os coeficientes de alta frequência (truncamento espectral), mantendo apenas os K primeiros que carregam a maior parte da energia.

**Pipeline:**
1. Normaliza a série para `[0, 1]` (`float32`)
2. Aplica DCT ortogonal (`scipy.fftpack.dct`, `norm='ortho'`)
3. Calcula K: coeficientes que cabem no tamanho-alvo (4 bytes por coeficiente — sem índice, pois são sequenciais)
4. Zera todos os coeficientes além da posição K
5. Aplica IDCT e reverte a normalização

**Parâmetros:**
| Parâmetro | Efeito |
|-----------|--------|
| `cr` | % de redução alvo. Controla K diretamente |

**Diferença-chave em relação à Wavelet:** Na DCT, os coeficientes mantidos são sempre os primeiros K (posições sequenciais), então não é necessário transmitir o índice de cada um — custo de 4 bytes por coeficiente vs. 8 na Wavelet. Isso torna a DCT mais eficiente em bits para o mesmo número de coeficientes, mas a estratégia de truncamento espectral é menos adaptável do que o hard thresholding por magnitude da Wavelet.

---

### 1.3 SDT (Segmented Data Transform / Método do Corredor)

**Princípio:** Algoritmo de streaming que processa a série ponto a ponto. Mantém um corredor angular em torno de uma linha reta partindo do último ponto salvo. Enquanto novos pontos cabem no corredor, eles são descartados. Quando um ponto viola o corredor, o último ponto válido é salvo e o corredor é reiniciado.

**Pipeline:**
1. Inicia com o primeiro ponto como âncora
2. Para cada novo ponto `p`, calcula as inclinações extremas (upper/lower slope) a partir dos pivôs do corredor (`âncora ± error`)
3. Atualiza `max_upper_slope` e `min_lower_slope`
4. Se `max_upper_slope > min_lower_slope`: o corredor foi violado → salva o último ponto inbound como keypoint, reinicia o corredor
5. O sinal é reconstruído por interpolação linear entre os keypoints

**Parâmetros:**
| Parâmetro | Efeito |
|-----------|--------|
| `error` | Desvio vertical máximo permitido. Maior `error` → corredor mais largo → menos keypoints → maior compressão |

**Controle de CR no experimento:** O SDT não tem `cr` como parâmetro direto. O `experiment.py` usa **busca binária** sobre `error` para atingir o `target_cr`, com tolerância de ±2% e até 30 iterações.

**Característica:** Algoritmo online (processa um ponto por vez, sem buffer). Muito eficiente em memória e tempo. A reconstrução linear pode introduzir artefatos em transições abruptas.

---

### 1.4 RDP (Ramer-Douglas-Peucker)

**Princípio:** Algoritmo de simplificação geométrica de curvas. Opera sobre a série inteira (offline). Encontra recursivamente o ponto de maior distância perpendicular à reta entre os extremos do segmento atual. Se essa distância excede `epsilon`, o ponto é mantido e a curva é dividida; caso contrário, todos os pontos intermediários são descartados.

**Pipeline:**
1. Recebe o segmento `[a, b]` (inicialmente toda a série)
2. Encontra o ponto `p` com maior distância perpendicular à reta `ab`
3. Se `dist(p) > epsilon`: mantém `p`, chama recursivamente `_rdp(a..p)` e `_rdp(p..b)`
4. Se `dist(p) <= epsilon`: descarta todos os intermediários, retorna apenas `[a, b]`
5. Reconstrói por interpolação linear entre os keypoints mantidos

**Parâmetros:**
| Parâmetro | Efeito |
|-----------|--------|
| `epsilon` | Distância perpendicular máxima tolerada. Menor `epsilon` → mais pontos mantidos → menor compressão |

**Controle de CR no experimento:** Mesma estratégia do SDT — busca binária sobre `epsilon`.

**Diferença em relação ao SDT:** O RDP é offline (precisa de toda a série), usa distância perpendicular (geométrica) ao invés de desvio vertical (algébrico), e tende a preservar melhor os picos e vales pronunciados. Em termos de complexidade: O(N log N) esperado, O(N²) no pior caso.

---

### 1.5 ARC-SDT (Adaptive Rate Control SDT)

**Princípio:** Extensão do SDT com malha de controle PID para ajustar dinamicamente o parâmetro `error` durante a compressão. O objetivo é convergir ao `target_cr` sem busca binária — o ajuste acontece em tempo real, enquanto o sinal é processado.

**Pipeline:**
1. Inicializa o `error` como `percentual_error × RMS_atual / 100`
2. Para cada novo ponto, executa o SDT normalmente
3. A cada `update_interval` pontos, mede a `current_cr` e calcula o erro de controle: `e = target_cr - current_cr`
4. O PID atualiza `percentual_error`:
   - `Δ = Kp·e + Ki·∫e + Kd·(de/dt)`
   - Com anti-windup (reset integral na troca de sinal do erro)
   - Com filtro derivativo de primeira ordem (α = 0.9)
   - Com saturação do output em `[1, 10000]`
5. O novo `error` absoluto é `max(percentual_error × RMS / 100, min_absolute_error)`

**Parâmetros:**
| Parâmetro | Valor padrão | Efeito |
|-----------|-------------|--------|
| `target_cr` | 80% | Taxa de compressão alvo |
| `kp` | 10.0 | Ganho proporcional — resposta imediata ao erro |
| `ki` | 2.0 | Ganho integral — elimina erro estacionário |
| `kd` | 0.0 | Ganho derivativo — amortece oscilações |
| `update_interval` | 1 | A cada quantos pontos o PID atualiza |
| `min_absolute_error` | 0.001 | Piso para o error absoluto (evita corredor nulo) |
| `percentual_error` | (= target_cr) | Erro inicial como % do RMS |

**Diferença do SDT puro:** O SDT usa busca binária antes da compressão para encontrar o `error` ideal. O ARC-SDT encontra esse `error` adaptativamente durante a compressão — adequado para aplicações online onde o `target_cr` deve ser atingido sem conhecimento prévio da série completa.

**Nota de implementação:** `percentual_error` no construtor de `ARCSDTCompressor` é inicializado com o valor de `target_cr` (linha 60), não com o parâmetro `percentual_error` recebido. Isso significa que a taxa inicial é usada como ponto de partida proporcional ao alvo.

---

## 2. O Experimento

### 2.1 Datasets

| Coleção | Pasta | Qtd. arquivos | Origem |
|---------|-------|--------------|--------|
| Pública | `public/datasets/` | 167 | Fontes acadêmicas (RAE, EcoData, GreenD, Indian, COMBED, Dryad, IDEAL, UKDALE, Smart*) |
| Privada | `private/datasets/` | 89 | Instalações brasileiras identificadas |

Cada arquivo é um JSON de 1.440 floats (potência em Watts, 1 leitura/minuto = 1 dia completo).

### 2.2 Combinações

O experimento é um produto cartesiano de:

| Dimensão | Valores | Qtd. |
|----------|---------|------|
| Algoritmos | wavelet-db4, wavelet-bior4.4, wavelet-sym4, DCT, ARC-SDT, SDT, RDP | 7 |
| Target CR | 10%, 20%, ..., 90% | 9 |
| Tamanhos de janela | 15, 60, 360, 720, 1440 pontos | 5 |

**Total de combinações por série:** 7 × 9 × 5 = **315 combinações**

Para 167 arquivos públicos e 89 privados:
- Público: 167 × 315 = ~52.605 execuções
- Privado: 89 × 315 = ~28.035 execuções

### 2.3 Janelamento

Cada arquivo (1.440 pontos) é dividido em janelas não-sobrepostas de tamanho fixo. Janelas incompletas ao final são descartadas. As métricas reportadas são a **média das janelas** da série.

| Janela | Qtd. janelas por série (1440 pts) | Interpretação |
|--------|----------------------------------|---------------|
| 15 pts | 96 | 15 minutos |
| 60 pts | 24 | 1 hora |
| 360 pts | 4 | 6 horas |
| 720 pts | 2 | 12 horas |
| 1440 pts | 1 | 1 dia completo |

O janelamento afeta diretamente a qualidade dos compressores baseados em transformada (Wavelet, DCT): janelas menores têm menos coeficientes disponíveis, limitando a resolução frequencial. Para compressores por corredor (SDT, RDP, ARC-SDT), janelas menores podem facilitar ou dificultar atingir o target\_cr dependendo da variabilidade local.

### 2.4 Controle de CR por algoritmo

| Algoritmo | Mecanismo |
|-----------|-----------|
| Wavelet | Direto via orçamento de bytes → K coeficientes |
| DCT | Direto via orçamento de bytes → K coeficientes |
| SDT | Busca binária sobre `error` (tolerância ±2%, até 30 iter.) |
| RDP | Busca binária sobre `epsilon` (tolerância ±2%, até 30 iter.) |
| ARC-SDT | Controle PID adaptativo durante a compressão |

### 2.5 Métricas coletadas por execução

**Desempenho:**
- `compression_ratio`: CR real atingido (%)
- `execution_time`: tempo total de todas as janelas (segundos)
- `memory_usage_mb`: pico de RAM acima da linha de base (MB)

**Qualidade de reconstrução:**

| Métrica | Fórmula resumida | Interpretação |
|---------|-----------------|---------------|
| MSE | mean((x - x̂)²) | Erro quadrático médio |
| RMSE | √MSE | Mesma unidade do sinal |
| NRMSE | RMSE / range(x) | RMSE normalizado pelo range |
| MAPE | mean(\|x-x̂\|/\|x\|)×100 | Erro percentual (exclui zeros) |
| ISD | sum((x - x̂)²) | Distância integral acumulada |
| PRD | 100 × ‖x-x̂‖ / ‖x‖ | Distorção relativa à norma L2 do sinal |
| SNR | 10 log₁₀(‖x‖² / ‖x-x̂‖²) | Relação sinal-ruído em dB |
| PSNR | 10 log₁₀(max(x)² / MSE) | SNR de pico em dB |
| SSIM | — | Similaridade estrutural (skimage) |
| EnergyError | 100 × \|E₁-E₂\| / E₁ | Erro relativo na energia total (%) |
| EnergyErrorTotal | igual com abs(x) | Erro na energia considerando valores absolutos |
| PeakRecall | picos preservados / picos originais | Fração dos picos recuperados |
| PeakAmplitudeError | erro médio na amplitude dos picos (%) | Fidelidade dos valores de pico |

**Detalhes das métricas de pico:**
- Pico detectado por `scipy.signal.find_peaks` com proeminência mínima de 10% do range
- Tolerância de posição: 1% do comprimento da janela (mínimo 1 amostra)
- Um pico original é "preservado" se existe ao menos um pico da série reconstruída dentro da tolerância

### 2.6 Saída

Arquivo CSV incremental em `experiments/resultados_publico.csv` ou `experiments/resultados_privado.csv`.

Colunas: `arquivo, data, metodo, algoritmo, target_cr, janela, compression_ratio, execution_time, memory_usage_mb, MSE, RMSE, NRMSE, MAPE, ISD, PRD, SNR, PSNR, SSIM, EnergyError, EnergyErrorTotal, PeakRecall, PeakAmplitudeError`

---

## 3. Visualizações Sugeridas

### 3.1 Trade-off CR × Qualidade

**O mais importante.** Para cada métrica de qualidade, plota a curva de degradação conforme o CR aumenta.

- **Tipo:** Linha, um traço por algoritmo
- **Eixo X:** `target_cr` (10% a 90%)
- **Eixo Y:** métrica (ex.: NRMSE, SSIM, PeakRecall)
- **Facets:** uma coluna por tamanho de janela
- **Dado:** mediana sobre todos os arquivos do dataset

```python
# Exemplo de estrutura
g = sns.FacetGrid(df, col="janela", height=4)
g.map_dataframe(sns.lineplot, x="target_cr", y="NRMSE", hue="algoritmo", estimator="median")
```

---

### 3.2 CR Real vs. CR Alvo

Verifica a fidelidade de cada algoritmo ao target solicitado — importante especialmente para SDT, RDP (busca binária) e ARC-SDT (PID).

- **Tipo:** Linha `y = x` (ideal) + pontos por algoritmo
- **Eixo X:** `target_cr`
- **Eixo Y:** `compression_ratio` (CR real médio)
- **Hue:** algoritmo
- **Interpretação:** desvio da diagonal = erro de controle sistemático

---

### 3.3 Radar / Spider Chart por Algoritmo

Visão multidimensional de cada algoritmo fixando CR e janela.

- **Eixos:** NRMSE, SSIM, PeakRecall, EnergyError, execution\_time normalizado, memory normalizado
- **Um polígono por algoritmo**
- Útil para resumo executivo: qual algoritmo domina em quê

---

### 3.4 Heatmap Algoritmo × Janela

Para um target\_cr fixo (ex.: 80%), mostra como a qualidade varia com o tamanho da janela para cada algoritmo.

- **Linhas:** algoritmo
- **Colunas:** janela (15, 60, 360, 720, 1440)
- **Célula:** mediana de NRMSE (ou outra métrica)
- **Colormap:** verde = melhor, vermelho = pior

---

### 3.5 Boxplot de Distribuição de Qualidade

Mostra a dispersão da qualidade entre séries para cada algoritmo — revela algoritmos que são bons na média mas instáveis.

- **Tipo:** Boxplot ou violin plot
- **Eixo X:** algoritmo
- **Eixo Y:** NRMSE (ou outra métrica)
- **Facets:** target\_cr (ou filtrar por um CR específico)

---

### 3.6 Pareto: CR × NRMSE

Plota os algoritmos no espaço CR real × NRMSE para identificar a fronteira de Pareto (máximo CR com mínimo erro).

- **Tipo:** Scatter, um ponto por (algoritmo, janela, target\_cr)
- **Destaque:** pontos na fronteira de Pareto
- **Utilidade:** identifica qual algoritmo é dominante para cada faixa de CR

---

### 3.7 Tempo de Execução vs. CR

- **Tipo:** Linha, um traço por algoritmo
- **Eixo X:** target\_cr
- **Eixo Y:** execution\_time (mediana, em ms por janela)
- **Insight esperado:** SDT e RDP crescem com CR baixo (mais iterações de busca binária); Wavelet e DCT têm tempo aproximadamente constante

---

### 3.8 Público vs. Privado

Compara se os algoritmos se comportam diferentemente nos dois datasets.

- **Tipo:** Barras side-by-side ou facets
- **Eixo X:** algoritmo
- **Eixo Y:** NRMSE mediano (fixando CR e janela)
- **Hue:** público / privado
- **Insight esperado:** dados privados (brasileiros) podem ter padrões distintos dos públicos

---

### 3.9 PeakRecall vs. EnergyError

Dois objetivos que podem conflitar: preservar picos (importante para faturamento de demanda) e conservar energia total (importante para faturamento de consumo).

- **Tipo:** Scatter 2D
- **Eixo X:** EnergyError (%)
- **Eixo Y:** PeakRecall (0–1)
- **Hue:** algoritmo
- **Facets:** target\_cr
- **Interpretação:** algoritmos no canto superior-esquerdo são os mais interessantes para o contexto de energia elétrica

---

### 3.10 JointGrid Comparativo (já implementado)

O `analysis/src/joint.py` gera JointGrids comparando dois algoritmos em NRMSE vs. CR real. Usar para comparações diretas entre pares de algoritmos de interesse (ex.: ARC-SDT vs. SDT, Wavelet-db4 vs. DCT).
