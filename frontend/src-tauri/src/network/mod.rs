mod config;
mod discovery;

pub use config::{
    gen_network_config_txt, get_api_url, get_config, load_config, set_role_client,
    set_role_server
};
pub use discovery::{
    discover_servers, iniciar_descoberta_servidores, parar_descoberta_servidores, EstadoDescoberta,
};
