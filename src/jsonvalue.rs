//! A small JSON value model and the byte exact rendering of the
//! Python json encoder as the report module calls it, with sorted
//! keys, two space indentation, and ASCII escaping.
//!
//! The escaping follows the encoder the Python standard library
//! ships. A quote and a backslash take a backslash. The control
//! characters with short forms use them, the remaining characters
//! outside the printable ASCII span take a four digit unicode
//! escape, and a character beyond the basic multilingual plane
//! takes a surrogate pair.

/// One JSON value. Object pairs keep their insertion order here,
/// and the rendering sorts them, as the encoder call in the
/// Python report module sorts them.
#[derive(Debug, Clone, PartialEq)]
pub enum JsonValue {
    Str(String),
    Int(i64),
    Bool(bool),
    List(Vec<JsonValue>),
    Object(Vec<(String, JsonValue)>),
}

fn escape_json_string(text: &str, out: &mut String) {
    out.push('"');
    for ch in text.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{8}' => out.push_str("\\b"),
            '\u{c}' => out.push_str("\\f"),
            ch if ('\u{20}'..='\u{7e}').contains(&ch) => out.push(ch),
            ch => {
                let code = ch as u32;
                if code <= 0xffff {
                    out.push_str(&format!("\\u{:04x}", code));
                } else {
                    let rest = code - 0x10000;
                    let high = 0xd800 + (rest >> 10);
                    let low = 0xdc00 + (rest & 0x3ff);
                    out.push_str(&format!("\\u{:04x}\\u{:04x}", high, low));
                }
            }
        }
    }
    out.push('"');
}

fn write_value(value: &JsonValue, level: usize, out: &mut String) {
    match value {
        JsonValue::Str(text) => escape_json_string(text, out),
        JsonValue::Int(number) => out.push_str(&number.to_string()),
        JsonValue::Bool(flag) => out.push_str(if *flag { "true" } else { "false" }),
        JsonValue::List(items) => {
            if items.is_empty() {
                out.push_str("[]");
                return;
            }
            out.push_str("[\n");
            let pad = "  ".repeat(level + 1);
            for (index, item) in items.iter().enumerate() {
                if index > 0 {
                    out.push_str(",\n");
                }
                out.push_str(&pad);
                write_value(item, level + 1, out);
            }
            out.push('\n');
            out.push_str(&"  ".repeat(level));
            out.push(']');
        }
        JsonValue::Object(pairs) => {
            if pairs.is_empty() {
                out.push_str("{}");
                return;
            }
            let mut sorted: Vec<&(String, JsonValue)> = pairs.iter().collect();
            sorted.sort_by(|a, b| a.0.cmp(&b.0));
            out.push_str("{\n");
            let pad = "  ".repeat(level + 1);
            for (index, (key, item)) in sorted.iter().enumerate() {
                if index > 0 {
                    out.push_str(",\n");
                }
                out.push_str(&pad);
                escape_json_string(key, out);
                out.push_str(": ");
                write_value(item, level + 1, out);
            }
            out.push('\n');
            out.push_str(&"  ".repeat(level));
            out.push('}');
        }
    }
}

/// Render a value the way the Python call renders it, with sorted
/// keys and two space indentation and no trailing newline.
pub fn dumps_sorted_indented(value: &JsonValue) -> String {
    let mut out = String::new();
    write_value(value, 0, &mut out);
    out
}
