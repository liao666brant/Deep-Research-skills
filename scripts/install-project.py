# /// script
# requires-python = ">=3.10"
# dependencies = ["json-five==1.1.2", "tomlkit==0.15.2"]
# ///

import argparse
import json
import stat
import tempfile
from collections.abc import Mapping
from pathlib import Path, PurePosixPath

import json5
import tomlkit
from json5.dumper import ModelDumper
from json5.loader import DefaultLoader, ModelLoader
from json5.model import DoubleQuotedString, JSONArray, JSONObject
from tomlkit.exceptions import TOMLKitError
from tomlkit.items import InlineTable


REPOSITORY = "liao666brant/Deep-Research-skills"
REPOSITORY_URL = f"https://github.com/{REPOSITORY}"
PLUGIN = "deep-research"
OPENCODE_PACKAGE = f"github:{REPOSITORY}"
CODEX_SOURCE = {
    "source": "git-subdir",
    "url": f"{REPOSITORY_URL}.git",
    "path": "./packages/codex",
}


def project_file(project, name):
    path = (project / name).resolve()
    if not path.is_relative_to(project):
        raise ValueError(f"配置文件位于项目之外：{path}")
    return path


def read_config(path, parse, default):
    if not path.exists():
        return "", default
    try:
        original = path.read_bytes().decode("utf-8")
        return original, parse(original)
    except (ValueError, SyntaxError, TOMLKitError) as error:
        raise ValueError(f"无法解析 {path}：{error}") from error


def save_config(path, original, updated):
    if updated == original:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=path.parent) as directory:
        temporary = Path(directory) / path.name
        temporary.write_bytes(updated.encode("utf-8"))
        if path.exists():
            temporary.chmod(stat.S_IMODE(path.stat().st_mode))
        temporary.replace(path)


def git_origin(url):
    return url.lower().rstrip("/").removeprefix("git+").removesuffix(".git")


def is_codex_source(project, source):
    if not isinstance(source, dict) or not isinstance(source.get("path"), str):
        return False
    path = PurePosixPath(source["path"])
    if path != PurePosixPath(CODEX_SOURCE["path"]):
        return False
    if source.get("source") == "local":
        return project == Path(__file__).resolve().parents[1] and (project / path / "plugin.json").is_file()
    url = source.get("url")
    return (
        source.get("source") == "git-subdir"
        and isinstance(url, str)
        and git_origin(url) == REPOSITORY_URL.lower()
    )


def install_codex(project):
    market_path = project_file(project, ".agents/plugins/marketplace.json")
    config_path = project_file(project, ".codex/config.toml")
    market_text, market = read_config(market_path, json.loads, {"name": "project-plugins", "plugins": []})
    config_text, config = read_config(config_path, tomlkit.parse, tomlkit.document())

    if not isinstance(market, dict) or not isinstance(market.get("name"), str) or not market["name"].strip():
        raise ValueError(f"{market_path} 需要提供市场名称 name")
    entries = market.setdefault("plugins", [])
    if not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries):
        raise ValueError(f"{market_path} 的 plugins 需要是对象数组")
    existing = [entry for entry in entries if entry.get("name") == PLUGIN]
    if any(not is_codex_source(project, entry.get("source")) for entry in existing):
        raise ValueError(f"{market_path} 中的同名插件 {PLUGIN} 存在来源冲突，未修改项目配置")

    plugin_id = f"{PLUGIN}@{market['name']}"
    plugins = config.setdefault("plugins", tomlkit.table())
    if not isinstance(plugins, Mapping):
        raise ValueError(f"{config_path} 的 plugins 需要是 TOML 表")
    if plugin_id not in plugins:
        plugins[plugin_id] = tomlkit.inline_table() if isinstance(plugins, InlineTable) else tomlkit.table()
    if not isinstance(plugins[plugin_id], Mapping):
        raise ValueError(f"{config_path} 中的 {plugin_id} 需要是 TOML 表")
    plugins[plugin_id]["enabled"] = True
    updated_config = tomlkit.dumps(config)

    if not existing:
        entries.append({
            "name": PLUGIN,
            "source": CODEX_SOURCE,
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        })
        save_config(market_path, market_text, json.dumps(market, ensure_ascii=False, indent=2) + "\n")
    save_config(config_path, config_text, updated_config)
    return config_path


def is_opencode_package(package):
    if not isinstance(package, str):
        return False
    origin, _, ref = package.partition("#")
    _, selector, subdirectory = ref.partition("::path:")
    if selector and (not subdirectory or PurePosixPath(subdirectory) != PurePosixPath(".")):
        return False
    return git_origin(origin) in (OPENCODE_PACKAGE.lower(), REPOSITORY_URL.lower())


def install_opencode(project):
    names = ("opencode.json", "opencode.jsonc", ".opencode/opencode.json", ".opencode/opencode.jsonc")
    paths = [project_file(project, name) for name in names if (project / name).exists()]
    if not paths:
        path = project_file(project, "opencode.json")
        data = {"plugins": [OPENCODE_PACKAGE]}
        save_config(path, "", json.dumps(data, indent=2) + "\n")
        return path

    loader = DefaultLoader()
    existing_path = None
    disabled_by = None
    for path in paths:
        original, document = read_config(path, lambda text: json5.loads(text, loader=ModelLoader()), None)
        if not isinstance(document.value, JSONObject):
            raise ValueError(f"{path} 需要是 JSON 对象")
        values = {loader.load(key): value for key, value in document.value.key_value_pairs}
        plugins = values.get("plugins")
        if plugins is not None and not isinstance(plugins, JSONArray):
            raise ValueError(f"{path} 的 plugins 需要是数组")
        entries = loader.load(plugins) if plugins is not None else []
        for entry in entries:
            package = entry.get("package") if isinstance(entry, dict) else entry
            if entry in (f"-{PLUGIN}", "-*"):
                disabled_by = (path, entry)
            elif package in (PLUGIN, "*"):
                disabled_by = None
            elif is_opencode_package(package):
                existing_path = path
                disabled_by = None

    if disabled_by is not None:
        disabled_path, selector = disabled_by
        raise ValueError(f"{disabled_path} 中的 {selector} 停用了 {PLUGIN}，未修改项目配置")
    if existing_path is not None:
        return existing_path

    # 在优先级最高的项目配置中写入插件条目。
    entry = DoubleQuotedString(OPENCODE_PACKAGE, raw_value=json.dumps(OPENCODE_PACKAGE))
    if plugins is None:
        key = DoubleQuotedString("plugins", raw_value='"plugins"')
        if document.value.keys:
            key.wsc_before = [" "]
        document.value.keys.append(key)
        document.value.values.append(JSONArray(entry))
    else:
        if plugins.values:
            entry.wsc_before = [" "]
        plugins.values.append(entry)
    save_config(path, original, json5.dumps(document, dumper=ModelDumper()))
    return path


def main():
    parser = argparse.ArgumentParser(description="为当前项目配置深度调研插件")
    parser.add_argument("host", choices=("codex", "opencode"))
    args = parser.parse_args()
    project = Path.cwd().resolve()
    try:
        install = install_codex if args.host == "codex" else install_opencode
        path = install(project)
    except (OSError, ValueError, TOMLKitError) as error:
        parser.exit(1, f"安装失败：{error}\n")
    print(f"已配置 {args.host} 项目插件（{path.relative_to(project)}）。请在此项目打开新会话以加载插件。")


if __name__ == "__main__":
    main()
