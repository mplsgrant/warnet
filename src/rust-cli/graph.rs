use anyhow::Context;
use clap::Subcommand;
use petgraph_graphml::GraphMl;
use rustworkx_core::generators::cycle_graph;
use rustworkx_core::petgraph;
use std::borrow::Cow;
use std::fs::File;
use std::io::Cursor;
use std::path::{Path, PathBuf};
use xmltree::{Element, EmitterConfig, XMLNode};

use crate::util::{dump_bitcoin_conf, parse_bitcoin_conf};
use rand::seq::SliceRandom;
use rand::thread_rng;

#[derive(Subcommand, Debug)]
pub enum GraphCommand {
    /// Create a cycle graph with <number> nodes, and include 7 extra random outbounds per node.
    /// Returns XML file as string with or without --outfile option
    Create {
        number: usize,
        #[arg(short, long)]
        outfile: Option<PathBuf>,
        #[arg(short, long)]
        version: Option<String>,
        #[arg(short, long)]
        bitcoin_conf: Option<PathBuf>,
    },
}

fn create_graph(number: usize) -> anyhow::Result<petgraph::graph::DiGraph<(), ()>> {
    // Create initial cycle graph
    let mut graph: petgraph::graph::DiGraph<(), ()> =
        cycle_graph(Some(number), None, || {}, || {}, false)
            .context("Create initial cycle graph")?;

    // Add more outbound connections to each node
    for node in graph.node_indices() {
        let mut candidates = Vec::new();
        for potential_target in graph.node_indices() {
            if node != potential_target && !graph.contains_edge(node, potential_target) {
                candidates.push(potential_target);
            }
        }
        // Add 7 extra outbounds
        for _ in 0..7 {
            if let Some(&random_target) = candidates.choose(&mut thread_rng()) {
                graph.add_edge(node, random_target, ());
                // Remove the selected target from candidates to avoid trying to add it again
                candidates.retain(|&x| x != random_target);
            }
        }
    }
    Ok(graph)
}

fn handle_bitcoin_conf(bitcoin_conf: Option<&Path>) -> String {
    // handle custom bitcoin.conf
    let mut conf_contents: String = String::new();
    if bitcoin_conf.is_some() {
        let conf = parse_bitcoin_conf(bitcoin_conf);
        // Iterate over sections and their properties
        for (section, prop) in &conf {
            println!("[{:?}]", section);
            for (key, value) in prop.iter() {
                println!("{}={}", key, value);
            }
        }
        conf_contents += &dump_bitcoin_conf(&conf);
    };
    conf_contents
}

pub async fn handle_graph_command(command: &GraphCommand) -> anyhow::Result<()> {
    match command {
        GraphCommand::Create {
            number,
            outfile,
            version,
            bitcoin_conf,
        } => {
            let version_str = version.as_deref().unwrap_or("26.0");
            let graph = create_graph(*number).context("creating graph")?;
            let bitcoin_conf = handle_bitcoin_conf(bitcoin_conf.as_deref());

            // Convert to graphml
            let graphml = GraphMl::new(&graph).pretty_print(true);
            let mut buf = Vec::new();
            graphml
                .to_writer(&mut buf)
                .expect("Failed to write GraphML data");

            let cursor = Cursor::new(buf);
            let mut graphml_element = Element::parse(cursor).unwrap();

            let keys = vec![
                ("version", "string"),
                ("bitcoin_config", "string"),
                ("tc_netem", "string"),
                ("build_args", "string"),
                ("exporter", "boolean"),
                ("collect_logs", "boolean"),
                ("image", "string"),
            ];
            for (attr_name, attr_type) in keys {
                let mut key_element = Element::new("key");
                key_element
                    .attributes
                    .insert("attr.name".to_string(), attr_name.to_string());
                key_element
                    .attributes
                    .insert("attr.type".to_string(), attr_type.to_string());
                key_element
                    .attributes
                    .insert("for".to_string(), "node".to_string());
                key_element
                    .attributes
                    .insert("id".to_string(), attr_name.to_string());

                graphml_element.children.push(XMLNode::Element(key_element));
            }
            // Find the <graph> element first
            if let Some(XMLNode::Element(graph_el)) = graphml_element
                .children
                .iter_mut()
                .find(|e| matches!(e, XMLNode::Element(el) if el.name == "graph"))
            {
                // iterate over the children of the <graph> element to find <node> elements
                for node in graph_el.children.iter_mut() {
                    if let XMLNode::Element(ref mut el) = node {
                        if el.name == "node" {
                            let data_elements = vec![
                                ("version", version_str),
                                ("bitcoin_config", bitcoin_conf.as_str()),
                                ("tc_netem", ""),
                                ("build_args", ""),
                                ("exporter", "false"),
                                ("collect_logs", "false"),
                                ("image", ""),
                            ];
                            for (key, value) in data_elements {
                                let mut data_element = Element::new("data");
                                data_element
                                    .attributes
                                    .insert("key".to_string(), key.to_string());
                                data_element.children.push(XMLNode::Text(value.to_string()));
                                el.children.push(XMLNode::Element(data_element));
                            }
                        }
                    }
                }
            }

            let config = EmitterConfig {
                write_document_declaration: true,
                perform_indent: true,
                indent_string: Cow::Borrowed("    "),
                line_separator: Cow::Borrowed("\n"),
                ..Default::default() // Keep other defaults
            };

            let mut buf_after = Vec::new();
            graphml_element
                .write_with_config(&mut buf_after, config.clone())
                .expect("Failed to write modified GraphML data");
            match outfile {
                Some(path) => {
                    let file = File::create(path).context("Writing final graphml file")?;
                    graphml_element.write_with_config(file, config)?;
                }
                None => {
                    // Write to stdout
                    let stdout = std::io::stdout();
                    let handle = stdout.lock();
                    graphml_element.write_with_config(handle, config)?;
                }
            }
        }
    }
    Ok(())
}