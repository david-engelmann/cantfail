//! ostensible asks whether a test can fail.
//!
//! This crate is the Rust port of the Python package of the same
//! name, built slice by slice against the landed Python, which
//! stands as the behavioural specification. This slice carries
//! the report reading whole and the collection settings reading
//! whole. The static scan and the Python source parser it
//! carries, the mutant generation, and the execution machinery
//! stay Python only, and the contract states that boundary by
//! name.

pub mod globmatch;
pub mod ini;
pub mod jsonvalue;
pub mod model;
pub mod pyvalue;
pub mod report;
pub mod settings;
pub mod toml;

pub use model::{
    aggregate_outcomes, Analysis, FileVerdict, FunctionVerdict, Mutant, MutantOutcome,
    StaticFinding,
};
pub use settings::{
    file_matches, load_collection_settings, load_collection_settings_with_source,
    name_matches, CollectionSettings,
};
