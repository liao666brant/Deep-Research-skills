import { readFile, readdir } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Plugin, Skill } from '@opencode/plugin';
import { parse } from 'yaml';

const skillsDirectory = fileURLToPath(new URL('./packages/claude-code/skills/', import.meta.url));

export default Plugin.define({
  id: 'deep-research',
  async setup(ctx) {
    const directories = await readdir(skillsDirectory, { withFileTypes: true });
    const skills = await Promise.all(directories.filter(entry => entry.isDirectory()).map(async entry => {
      const path = join(skillsDirectory, entry.name, 'SKILL.md');
      const markdown = await readFile(path, 'utf8');
      const frontmatter = /^---\r?\n([\s\S]+?)\r?\n---\r?\n/.exec(markdown);
      if (!frontmatter) throw new Error(`技能文件缺少 YAML 元数据：${path}`);
      const { name, description } = parse(frontmatter[1]);

      return {
        id: Skill.ID.make(name),
        name: Skill.Name.make(name),
        description,
        path: Skill.Info.fields.path.make(path),
        content: markdown.slice(frontmatter[0].length),
      };
    }));

    await ctx.skill.transform(editor => {
      for (const skill of skills) editor.add(skill);
    });
  },
});
