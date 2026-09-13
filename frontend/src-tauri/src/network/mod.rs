mod config;
mod discovery;
mod local_ip;
mod log;

// `gen_network_config_txt`/`discover_servers` só são usados no setup de release.
#[cfg_attr(debug_assertions, allow(unused_imports))]
pub use config::{
    diagnostico_rede, gen_network_config_txt, get_api_url, get_config, load_config,
    resolver_papel_efetivo, salvar_config, set_role_client, set_role_server, get_config_dir,
};
#[cfg_attr(debug_assertions, allow(unused_imports))]
pub use discovery::{
    discover_servers, iniciar_descoberta_servidores, parar_descoberta_servidores, EstadoDescoberta,
};
pub use local_ip::ip_lan_privado;
pub use log::{iniciar_log, ler_log, log_rede};
