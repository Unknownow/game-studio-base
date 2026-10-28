import unittest

from gamestudio import frontmatter


class FrontmatterTest(unittest.TestCase):
    def test_scalars_strings_lists_nested(self):
        text = '---\nname: dev-story\ndescription: "Has a \\"quote\\" inside"\ncan: [read, write]\nmemory: true\nmetadata:\n  upstream: .claude/x\n  core: "true"\n# comment\n---\nbody\n'
        data, body = frontmatter.parse(text)
        self.assertEqual(data["name"], "dev-story")
        self.assertEqual(data["description"], 'Has a "quote" inside')
        self.assertEqual(data["can"], ["read", "write"])
        self.assertIs(data["memory"], True)
        self.assertEqual(data["metadata"], {"upstream": ".claude/x", "core": "true"})
        self.assertEqual(body.strip(), "body")

    def test_inline_comment_and_quoted_list_items(self):
        data, _ = frontmatter.parse('---\npaths: ["src/**", "a, b"]  # why\nname: x # c\n---\n')
        self.assertEqual(data["paths"], ["src/**", "a, b"])
        self.assertEqual(data["name"], "x")

    def test_block_scalar_is_error_with_line(self):
        with self.assertRaises(frontmatter.FrontmatterError) as cm:
            frontmatter.parse("---\nname: x\ndescription: |\n  long\n---\n")
        self.assertEqual(cm.exception.line, 3)

    def test_no_frontmatter(self):
        data, body = frontmatter.parse("# Title\n")
        self.assertIsNone(data)

    def test_unclosed(self):
        with self.assertRaises(frontmatter.FrontmatterError):
            frontmatter.parse("---\nname: x\n")


if __name__ == "__main__":
    unittest.main()
