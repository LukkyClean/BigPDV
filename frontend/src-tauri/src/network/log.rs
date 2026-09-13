//! Log persistente das decisões de rede (papel da máquina, URL, health, sidecar).
//!
//! Em release o app roda com `windows_subsystem = "windows"`: todo `println!` se
//! perde. Este arquivo é o que permite ao suporte entender, na máquina do cliente,
//! por que o app decidiu ser terminal/servidor e onde tentou falar com o backend.
//! Fica ao lado do `system-config.json`, com rotação simples por tamanho.

use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use std::sync::OnceLock;

const NOME_ARQUIVO: &str = "rede.log";
const TAMANHO_MAXIMO: u64 = 1024 * 1024; // 1 MB

static CAMINHO: OnceLock<PathBuf> = OnceLock::new();

/// Define a pasta do log. Chamar uma vez no `setup`, antes de qualquer `log_rede`.
pub fn iniciar_log(pasta: PathBuf) {
    let _ = fs::create_dir_all(&pasta);
    let _ = CAMINHO.set(pasta.join(NOME_ARQUIVO));
}

pub fn caminho_log() -> Option<PathBuf> {
    CAMINHO.get().cloned()
}

pub fn log_rede(mensagem: &str) {
    let linha = format!(
        "{} {}",
        chrono::Local::now().format("%Y-%m-%d %H:%M:%S"),
        mensagem
    );
    println!("[rede] {}", mensagem);

    let Some(caminho) = CAMINHO.get() else {
        return;
    };

    rotacionar_se_preciso(caminho);

    if let Ok(mut arquivo) = OpenOptions::new().create(true).append(true).open(caminho) {
        let _ = writeln!(arquivo, "{}", linha);
    }
}

fn rotacionar_se_preciso(caminho: &PathBuf) {
    let Ok(meta) = fs::metadata(caminho) else {
        return;
    };
    if meta.len() < TAMANHO_MAXIMO {
        return;
    }
    let antigo = caminho.with_extension("log.1");
    let _ = fs::remove_file(&antigo);
    let _ = fs::rename(caminho, antigo);
}

/// Últimas `max_linhas` do log — usado pelo painel de diagnóstico.
pub fn ler_log(max_linhas: usize) -> String {
    let Some(caminho) = CAMINHO.get() else {
        return String::new();
    };
    let Ok(conteudo) = fs::read_to_string(caminho) else {
        return String::new();
    };
    let linhas: Vec<&str> = conteudo.lines().collect();
    let inicio = linhas.len().saturating_sub(max_linhas);
    linhas[inicio..].join("\n")
}
