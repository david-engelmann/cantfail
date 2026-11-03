//! The thin binary shell over the library. This slice gives the
//! library one behaviour that takes filesystem input end to end,
//! the collection settings reading, and the shell carries that
//! reading alone. It takes the project folder as its single
//! argument and prints what that folder resolves to, one line
//! for each setting the resolved settings carry a stated value
//! for, in the order the settings module orders its keys, and a
//! closing line naming the source that decided the folder, or
//! the word none where no source decided it.

use std::path::Path;
use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 2 {
        eprintln!("usage: cantfail <project folder>");
        return ExitCode::from(2);
    }
    let (settings, source) =
        cantfail::settings::load_collection_settings_with_source(Path::new(&args[1]));
    for key in cantfail::settings::KEYS {
        if let Some(patterns) = settings.get(key) {
            println!("{} = {}", key, patterns.join(" "));
        }
    }
    match source {
        Some(path) => println!("source = {}", path.display()),
        None => println!("source = none"),
    }
    ExitCode::SUCCESS
}
