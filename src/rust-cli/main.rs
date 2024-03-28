use clap::{Parser, Subcommand};
use anyhow::Context;

mod debug;
mod general;
mod network;
mod rpc_call;
mod scenarios;
mod util;
use crate::debug::{handle_debug_command, DebugCommand};
use crate::general::*;
use crate::network::{handle_network_command, NetworkCommand};
use crate::scenarios::{handle_scenario_command, ScenarioCommand};

#[derive(Parser, Debug)]
#[command(version, about, long_about = None)]
struct Cli {
    #[arg(long, default_value = "warnet")]
    network: String,

    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// Network commands
    Network {
        #[command(subcommand)]
        command: Option<NetworkCommand>,
    },
    /// Debug commands [[deprecated]]
    Debug {
        #[command(subcommand)]
        command: Option<DebugCommand>,
    },
    /// Scenario commands
    Scenarios {
        #[command(subcommand)]
        command: Option<ScenarioCommand>,
    },
    /// Call bitcoin-cli <method> [params] on <node> in [network]
    Rpc {
        node: u64,
        method: String,
        params: Option<Vec<String>>,
    },
    /// Call lncli <method> [params] on <node> in [network]
    LnCli {
        node: u64,
        method: String,
        params: Option<Vec<String>>,
    },
    /// Fetch the Bitcoin Core debug log from <node> in [network]
    DebugLog {
        node: u64,
    },
    /// Fetch messages sent between <node_a> and <node_b> in [network]
    Messages {
        node_a: u64,
        node_b: u64,
    },
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    let mut rpc_params = jsonrpsee::core::params::ObjectParams::new();
    rpc_params
        .insert("network", &cli.network)
        .context("add network param")?;

    match &cli.command {
        Some(Commands::Network { command }) => {
            if let Some(command) = command {
                handle_network_command(command, rpc_params).await?;
            }
        }
        Some(Commands::Debug { command }) => {
            if let Some(command) = command {
                handle_debug_command(command, rpc_params).await?;
            }
        }
        Some(Commands::Scenarios { command }) => {
            if let Some(command) = command {
                handle_scenario_command(command, rpc_params).await?;
            }
        }
        Some(Commands::Rpc {
            node,
            method,
            params,
        }) => {
            handle_rpc_commands(NodeType::BitcoinCli, node, method, params, rpc_params).await?;
        }
        Some(Commands::LnCli {
            node,
            method,
            params,
        }) => {
            handle_rpc_commands(NodeType::LnCli, node, method, params, rpc_params).await?;
        }
        Some(Commands::DebugLog { node }) => {
            handle_debug_log_command(node, rpc_params).await?;
        }
        Some(Commands::Messages { node_a, node_b }) => {
            handle_messages_command(node_a, node_b, rpc_params).await?;
        }
        None => println!("No command provided"),
    }

    Ok(())
}