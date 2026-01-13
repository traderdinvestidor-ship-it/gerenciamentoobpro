class SorosGaleSession:
    def __init__(self, banca, payout, entrada_base, nivel_max_soros, fator_gale=1.0, perc_soros=100.0, reiniciar_apos_gale=True, estrategia_gale="Padrão", fator_gale_1=0.5, meta_lucro=0.0, entrada_is_percent=False):
        self.banca = banca
        self.payout = payout / 100.0
        self.entrada_base = entrada_base
        self.nivel_max_soros = nivel_max_soros
        self.fator_gale = fator_gale 
        self.perc_soros = perc_soros / 100.0
        self.reiniciar_apos_gale = reiniciar_apos_gale
        self.meta_lucro = meta_lucro # Meta de Lucro em R$
        
        # Estratégia de Gale
        # "Padrão": Recuperação Imediata.
        # "Suave (2 Níveis)": Gale 1 = Fração da Perda (ex: 50%).
        # "Gale no 2º Loss": Gale 1 = Entrada Base. Só faz Gale pesado se perder 2 seguidas.
        # "SorosGale (Recuperação 2x)": Acumula perda até 2 wins seguidos.
        self.estrategia_gale = estrategia_gale
        self.fator_gale_1 = fator_gale_1 
        
        # Estado atual
        self.historico = []
        self.saldo_sessao = 0.0
        self.nivel_soros_atual = 1 
        self.tentativa_gale_atual = 0 # Contador visual de "Nível de Risco/Tentativa"
        
        self.lucro_acumulado_soros = 0.0 
        self.perda_no_nivel_atual = 0.0
        
        # Estado Específico para "Recuperação 2x" (Vídeo)
        self.em_recuperacao = False
        self.passo_recuperacao = 0 # 1 ou 2
        self.entrada_recup_step1 = 0.0
        
        # Estado Específico para "4x (Senhor Trader)"
        self.step_4x = 1 # 1, 2, 3, 4
        self.subsolo_step = 0 # 0, 1, 2 (Gales)
        self.meta_cheia = False

        # Novo Flag de Encerramento (Meta Batida)
        self.sessao_encerrada = False
        
        self.entrada_is_percent = entrada_is_percent
        self.proxima_entrada = self.entrada_base
        if self.entrada_is_percent:
            self.proxima_entrada = (self.banca + self.saldo_sessao) * (self.entrada_base / 100.0)
            if self.proxima_entrada < 2.0: self.proxima_entrada = 2.0
            
        self.mensagem_estado = "Início: Passo 1"

        # --- SACAC (Proteção de Degraus) ---
        self.sacac_mode = False
        self.sacac_step = 0.0
        self.sacac_base = banca
        self.sacac_piso = 0.0
        self.sacac_alvo = 0.0 # Inicializa aqui, mas será configurado por _configurar_sacac
        
        self._configurar_sacac(estrategia_gale)

    def _configurar_sacac(self, strat):
        if "SACAC" in strat:
            self.sacac_mode = True
            if "Dezena" in strat: self.sacac_step = 50.0
            elif "Centena" in strat: self.sacac_step = 100.0
            elif "Milhar" in strat: self.sacac_step = 1000.0
            else: self.sacac_step = 50.0 # Default
            
            self.sacac_piso = self.sacac_base - self.sacac_step
            self.sacac_alvo = self.sacac_base + self.sacac_step

    def registrar_win(self):
        entrada_real = self.proxima_entrada
        lucro = entrada_real * self.payout
        self.saldo_sessao += lucro
        
        # Identificação da Fase para o Histórico
        fase_label = ""
        if self.estrategia_gale == "4x (Senhor Trader)":
            if self.subsolo_step > 0:
                fase_label = f"Subsolo G{self.subsolo_step}"
            else:
                fase_label = f"Passo {self.step_4x}"
        elif self.em_recuperacao:
            fase_label = f"Recup {self.passo_recuperacao}/2"
        else:
            fase_label = f"Nível {self.nivel_soros_atual}"

        info = {
            "Nível Soros": fase_label,
            "Gale": self.tentativa_gale_atual,
            "Entrada": entrada_real,
            "Resultado": "WIN",
            "Saldo Sessão": self.saldo_sessao
        }
        self.historico.append(info)
        
        # --- Lógica 4x (Senhor Trader) ---
        if self.estrategia_gale == "4x (Senhor Trader)":
            if self.subsolo_step > 0:
                # Ganhou no Subsolo! Volta para o Passo 1
                self.subsolo_step = 0
                self.step_4x = 1
                self.perda_no_nivel_atual = 0.0
                self.tentativa_gale_atual = 0
                self.mensagem_estado = "Subsolo Recuperado! Voltando ao Passo 1."
            else:
                # Ganhou na sequência principal
                if self.step_4x == 1:
                    self.step_4x = 2
                    self.mensagem_estado = "Passo 2 (Soros)"
                elif self.step_4x == 2:
                    self.step_4x = 3
                    self.mensagem_estado = "Passo 3 (Inverso 1)"
                elif self.step_4x == 3:
                    self.step_4x = 4
                    self.mensagem_estado = "Passo 4 (Inverso 2)"
                elif self.step_4x == 4:
                    self.step_4x = 1 # Reset automático para fluidez
                    self.mensagem_estado = "Passo 1"
            
            self._atualizar_entrada()
            return

        if self.sacac_mode:
            # SACAC não usa ciclos de Soros nem metas de 'nível'
            self.mensagem_estado = "Operação SACAC"
        elif self.estrategia_gale == "SorosGale (Recuperação 2x)" and self.em_recuperacao:
            # Lógica de Recuperação do Vídeo _YFSrmtxww0 (2 Passos por Nível de SG)
            if self.passo_recuperacao == 1:
                self.passo_recuperacao = 2
                self.mensagem_estado = "Recup Passo 2"
            else:
                # Fim do Nível de Recuperação (Sucesso do SG XX)
                self.em_recuperacao = False
                self.passo_recuperacao = 0
                self.perda_no_nivel_atual = 0.0
                self.tentativa_gale_atual = 0
                self.nivel_soros_atual = 1
                self.lucro_acumulado_soros = 0.0
                self.mensagem_estado = "Passo 1"
        else:
            # Modo Soros Padrão (Normal Cycle: 2 Níveis p/ "Recuperação 2x")
            max_niveis = 2 if self.estrategia_gale == "SorosGale (Recuperação 2x)" else self.nivel_max_soros
            
            cost_level = self.perda_no_nivel_atual
            net_level = lucro - cost_level
            
            if self.tentativa_gale_atual > 0 and self.estrategia_gale != "SorosGale (Recuperação 2x)":
                 # ... (Lógica para outros Gales)
                 self.perda_no_nivel_atual = 0.0
                 self.tentativa_gale_atual = 0
                 if self.reiniciar_apos_gale:
                     self.nivel_soros_atual = 1
                     self.lucro_acumulado_soros = 0.0
                     self.mensagem_estado = "Passo 1"
                 else:
                     self.mensagem_estado = "Gale Recuperado. Nível Mantido."
            else:
                self.perda_no_nivel_atual = 0.0 
                self.lucro_acumulado_soros += (net_level * self.perc_soros)
                self.nivel_soros_atual += 1
                
                if self.nivel_soros_atual > max_niveis:
                    self.nivel_soros_atual = 1
                    self.lucro_acumulado_soros = 0.0
                    self.mensagem_estado = "🏆 Meta Batida! (Reiniciando)"
                else:
                    self.mensagem_estado = f"Soros Nível {self.nivel_soros_atual}"
        
        # --- Meta Financeira (Stop Win R$) ---
        if self.meta_lucro > 0 and self.saldo_sessao >= self.meta_lucro:
            self.mensagem_estado = f"Meta R$ {self.meta_lucro} (Acima)"
            self._atualizar_entrada()
            return

        # --- SACAC Win Logic (Target Reached) ---
        if self.sacac_mode and not self.sessao_encerrada:
            banca_atual = self.banca + self.saldo_sessao
            if banca_atual >= self.sacac_alvo:
                self.sacac_piso = self.sacac_base # Piso vira a base anterior (Protege a dezena)
                self.sacac_base = self.sacac_alvo
                self.sacac_alvo = self.sacac_base + self.sacac_step
                self.mensagem_estado = f"🛡️ Degrau SACAC Concluído! Novo Piso Protegido: R$ {self.sacac_piso:.2f}"
                # REMOVIDO: sessao_encerrada = True (Permite continuar operando conforme solicitado)

        self._atualizar_entrada()

    def registrar_loss(self):
        entrada_real = self.proxima_entrada
        self.saldo_sessao -= entrada_real
        self.perda_no_nivel_atual += entrada_real
        
        # Label para Histórico 4x
        fase_label = ""
        if self.estrategia_gale == "4x (Senhor Trader)":
            if self.subsolo_step > 0:
                fase_label = f"Subsolo G{self.subsolo_step}"
            else:
                fase_label = f"Passo {self.step_4x}"
        elif self.em_recuperacao:
            fase_label = f"Recup {self.passo_recuperacao}/2"
        else:
            fase_label = f"Nível {self.nivel_soros_atual}"

        info = {
            "Nível Soros": fase_label,
            "Gale": self.tentativa_gale_atual,
            "Entrada": entrada_real,
            "Resultado": "LOSS",
            "Saldo Sessão": self.saldo_sessao
        }
        self.historico.append(info)
        
        # --- Lógica 4x (Senhor Trader) ---
        if self.estrategia_gale == "4x (Senhor Trader)":
            if self.subsolo_step > 0:
                if self.subsolo_step == 1:
                    self.subsolo_step = 2
                    self.mensagem_estado = "Subsolo G2 (Última Chance)"
                else:
                    self.mensagem_estado = "Passo 1"
                    self.subsolo_step = 0
                    self.step_4x = 1
            else:
                if self.step_4x in [1, 2]:
                    # Perdeu no início -> Subsolo
                    self.subsolo_step = 1
                    self.nivel_soros_atual = 1
                    self.lucro_acumulado_soros = 0.0
                    self.mensagem_estado = "Recup 1 (Subsolo)"
                elif self.step_4x == 3:
                    # Perdeu no Inverso 1 -> Volta pro 2
                    self.step_4x = 2
                    self.mensagem_estado = "Loss no Inverso 1! 🛑 ALERTA: PARAR"
                elif self.step_4x == 4:
                    # Perdeu no Inverso 2 -> Volta pro 3
                    self.step_4x = 3
                    self.mensagem_estado = "Loss no Inverso 2! 🛑 ALERTA: PARAR"
            
            self._atualizar_entrada()
            return

        # --- Lógica Stop Loss (Outros Modos) ---
        should_stop = False
        if self.sacac_mode:
            # SACAC não usa limites de gale nem stop loss fixo de 2 perdas
            self.mensagem_estado = "SACAC: Protegendo Capital"
            self._atualizar_entrada()
        elif self.estrategia_gale == "SorosGale (Recuperação 2x)":
            if not self.em_recuperacao:
                # Primeiro Loss -> Inicia SG 01
                self.em_recuperacao = True
                self.passo_recuperacao = 1
                self.tentativa_gale_atual = 1 # SG Level
                self.nivel_soros_atual = 1
                self.lucro_acumulado_soros = 0.0
                self.mensagem_estado = "SG 1 - Passo 1"
            else:
                # Perdeu durante um SG -> Vai para o próximo nível (SG 02, 03...)
                # No SG, se perder qualquer uma das duas mãos, sobe o nível
                self.passo_recuperacao = 1
                self.tentativa_gale_atual += 1 # Próximo Nível SG
                self.mensagem_estado = f"SG {self.tentativa_gale_atual} 🛑 Recomenda Parar"
        else:
            self.tentativa_gale_atual += 1
            if self.tentativa_gale_atual >= 2:
                 should_stop = True
                 self.mensagem_estado = "🛑 Recomenda Parar (Limite de Gales)"
            else:
                 self.mensagem_estado = f"Gale {self.tentativa_gale_atual} (Proteção)"

        if should_stop:
            self.mensagem_estado = "Passo 1"
            self.tentativa_gale_atual = 0
            self.nivel_soros_atual = 1
            self.proxima_entrada = self.entrada_base 
        elif not self.sacac_mode:
            self._atualizar_entrada()

        # --- SACAC Loss Logic (Floor Protection) ---
        if self.sacac_mode:
            banca_atual = self.banca + self.saldo_sessao
            if banca_atual <= self.sacac_piso:
                self.mensagem_estado = "Piso Redefinido"

    def _atualizar_entrada(self):
        # 0. Cálculo da Entrada Base Dinâmica (George Soros)
        base_atual = self.entrada_base
        if self.entrada_is_percent:
            banca_comp = self.banca + self.saldo_sessao
            base_atual = (banca_comp * (self.entrada_base / 100.0))
            if base_atual < 2.0: base_atual = 2.0

        # --- Lógica SACAC (Risco do Excedente) ---
        if self.sacac_mode:
            banca_atual = self.banca + self.saldo_sessao
            if banca_atual > self.sacac_base:
                # Arrisca apenas o lucro acima da base protegida
                self.proxima_entrada = banca_atual - self.sacac_base
                self.mensagem_estado = f"🎯 Riscando Lucro Acumulado (R$ {self.proxima_entrada:.2f})"
            else:
                # Arrisca o buffer entre o saldo atual e o piso
                self.proxima_entrada = banca_atual - self.sacac_piso
                self.mensagem_estado = f"🛡️ Riscando Buffer! (R$ {self.proxima_entrada:.2f}) 🛑 ALERTA: PARAR"
            
            # Garantia de entrada mínima (evitar 0 ou negativo caso o sistema erre o piso)
            if self.proxima_entrada <= 0:
                self.proxima_entrada = 2.0 # Mínimo corretora
                self.mensagem_estado = "⚠️ Saldo no Limite do Piso! Entrada Mínima."
            return

        # --- Lógica 4x (Senhor Trader) ---
        if self.estrategia_gale == "4x (Senhor Trader)":
            if self.subsolo_step > 0:
                # Recuperar a perda total da sessão + pequena margem
                # No Subsolo, queremos voltar pro 0x0 ou lucro leve
                # Entry = Perda Acumulada / Payout
                perda_total_efetiva = self.perda_no_nivel_atual
                self.proxima_entrada = perda_total_efetiva / self.payout
                return
            
            # Sequência Principal
            if self.step_4x == 1:
                self.proxima_entrada = self.entrada_base
            elif self.step_4x == 2:
                # Soros: Entrada + Lucro do Passo 1
                lucro_1 = self.entrada_base * self.payout
                self.proxima_entrada = self.entrada_base + lucro_1
            elif self.step_4x == 3:
                # Inverso 1: Apenas o Lucro do Passo 2 (Soros)
                # O Passo 2 foi (Base + Lucro1), lucro dele é (Base + Lucro1) * Payout
                entrada_2 = self.entrada_base + (self.entrada_base * self.payout)
                lucro_2 = entrada_2 * self.payout
                self.proxima_entrada = lucro_2
            elif self.step_4x == 4:
                # Inverso 2: Apenas o Lucro do Passo 3
                # Pegamos a entrada do passo 3 e calculamos o lucro
                # (Dinamizando pra caso o Payout mude no meio, mas usando o atual pra estimar)
                # Na verdade, o histórico pode ter o lucro real, mas vamos usar o calculo teorico:
                entrada_3_teorica = (self.entrada_base + (self.entrada_base * self.payout)) * self.payout
                lucro_3 = entrada_3_teorica * self.payout
                self.proxima_entrada = lucro_3
            return

        # 1. Modo Soros (Normal)
        if not self.em_recuperacao and self.tentativa_gale_atual == 0:
            if self.nivel_soros_atual == 1:
                self.proxima_entrada = base_atual
            else:
                # Soros: Entrada = Entrada Base + Lucro Acumulado do Soros
                self.proxima_entrada = base_atual + self.lucro_acumulado_soros
        # 2. Modo Recuperação Multi-Nível (Video _YFSrmtxww0)
        elif self.em_recuperacao:
            # sg_level = self.tentativa_gale_atual
            # Primeira entrada do SG 01 é 50% da entrada base (conforme vídeo exemplo 4.00 -> 2.00)
            # A progressão é 1.5x a cada nível inicial
            base_sg = base_atual * 0.5
            entrada_step1 = base_sg * (1.5 ** (self.tentativa_gale_atual - 1))
            
            if self.passo_recuperacao == 1:
                self.proxima_entrada = entrada_step1
            else:
                # Passo 2 (Soros do SG): Entrada + Lucro do passo 1
                lucro_step1 = entrada_step1 * self.payout
                self.proxima_entrada = entrada_step1 + lucro_step1
        # 3. Modo Gale (Padrão, Suave, Gale no 2º Loss)
        elif self.tentativa_gale_atual > 0:
            if self.estrategia_gale == "Padrão":
                # Gale Padrão: Recupera a perda do nível atual + entrada base
                # Entrada = (Perda_no_nivel_atual + Entrada_Base) / Payout
                self.proxima_entrada = (self.perda_no_nivel_atual + self.entrada_base) / self.payout
            elif self.estrategia_gale == "Suave (2 Níveis)":
                if self.tentativa_gale_atual == 1:
                    # Gale 1: Recupera uma fração da perda
                    self.proxima_entrada = (self.perda_no_nivel_atual * self.fator_gale_1) / self.payout
                else:
                    # Gale 2: Recupera o restante da perda + entrada base
                    self.proxima_entrada = (self.perda_no_nivel_atual + self.entrada_base) / self.payout
            elif self.estrategia_gale == "Gale no 2º Loss":
                if self.tentativa_gale_atual == 1:
                    # Primeiro Loss: Entrada Base (não é um gale de recuperação ainda)
                    self.proxima_entrada = self.entrada_base
                else:
                    # Segundo Loss (Gale): Recupera a perda acumulada + entrada base
                    self.proxima_entrada = (self.perda_no_nivel_atual + self.entrada_base) / self.payout
            else:
                # Fallback para qualquer outro gale não especificado
                self.proxima_entrada = (self.perda_no_nivel_atual + self.entrada_base) / self.payout

        # Garante que a entrada não seja negativa ou zero
        self.proxima_entrada = max(0.01, round(self.proxima_entrada, 2))


    # --- PERSISTÊNCIA ---
    def to_dict(self):
        return {
            "banca": self.banca,
            "payout": self.payout * 100, # Voltando pra %
            "entrada_base": self.entrada_base,
            "nivel_max_soros": self.nivel_max_soros,
            "fator_gale": self.fator_gale,
            "perc_soros": self.perc_soros * 100,
            "reiniciar_apos_gale": self.reiniciar_apos_gale,
            "estrategia_gale": self.estrategia_gale,
            "fator_gale_1": self.fator_gale_1,
            "historico": self.historico,
            "saldo_sessao": self.saldo_sessao,
            "nivel_soros_atual": self.nivel_soros_atual,
            "tentativa_gale_atual": self.tentativa_gale_atual,
            "lucro_acumulado_soros": self.lucro_acumulado_soros,
            "perda_no_nivel_atual": self.perda_no_nivel_atual,
            "em_recuperacao": self.em_recuperacao,
            "passo_recuperacao": self.passo_recuperacao,
            "entrada_recup_step1": self.entrada_recup_step1,
            "sessao_encerrada": self.sessao_encerrada,
            "mensagem_estado": self.mensagem_estado,
            "proxima_entrada": self.proxima_entrada,
            "meta_lucro": self.meta_lucro,
            "entrada_is_percent": self.entrada_is_percent,
            "step_4x": self.step_4x,
            "subsolo_step": self.subsolo_step,
            "sacac_mode": self.sacac_mode,
            "sacac_step": self.sacac_step,
            "sacac_base": self.sacac_base,
            "sacac_piso": self.sacac_piso,
            "sacac_alvo": self.sacac_alvo
        }

    @classmethod
    def from_dict(cls, data):
        # Cria nova instância com dados básicos
        session = cls(
            data["banca"], data["payout"], data["entrada_base"], data["nivel_max_soros"],
            data["fator_gale"], data["perc_soros"], data["reiniciar_apos_gale"], 
            data["estrategia_gale"], data.get("fator_gale_1", 0.5), data.get("meta_lucro", 0.0),
            data.get("entrada_is_percent", False)
        )
        # Restaura estado dinâmico
        session.historico = data["historico"]
        session.saldo_sessao = data["saldo_sessao"]
        session.nivel_soros_atual = data["nivel_soros_atual"]
        session.tentativa_gale_atual = data["tentativa_gale_atual"]
        session.lucro_acumulado_soros = data["lucro_acumulado_soros"]
        session.perda_no_nivel_atual = data["perda_no_nivel_atual"]
        session.em_recuperacao = data["em_recuperacao"]
        session.passo_recuperacao = data["passo_recuperacao"]
        session.entrada_recup_step1 = data["entrada_recup_step1"]
        session.sessao_encerrada = data["sessao_encerrada"]
        session.mensagem_estado = data["mensagem_estado"]
        session.proxima_entrada = data["proxima_entrada"]
        session.meta_lucro = data.get("meta_lucro", 0.0)
        session.step_4x = data.get("step_4x", 1)
        session.subsolo_step = data.get("subsolo_step", 0)
        session.sacac_mode = data.get("sacac_mode", False)
        session.sacac_step = data.get("sacac_step", 0.0)
        session.sacac_base = data.get("sacac_base", data.get("banca", 100.0))
        session.sacac_piso = data.get("sacac_piso", 0.0)
        session.sacac_alvo = data.get("sacac_alvo", 0.0)
        return session
            
    def get_status(self):
        return {
            "Entrada Sugerida": round(self.proxima_entrada, 2),
            "Fase": f"Soros {self.nivel_soros_atual} | Gale {self.tentativa_gale_atual}",
            "Mensagem": self.mensagem_estado,
            "Saldo Sessão": round(self.saldo_sessao, 2)
        }
