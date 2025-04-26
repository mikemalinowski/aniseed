import aniseed_toolkit


class ToolApiDocumentationGenerator(aniseed_toolkit.Tool):

    identifier = "Update Aniseed Toolkit Api Documentation"
    classification = "Documentation"
    user_facing = False

    def run(self):
        """
        This will update the tool doc's in teh _resources/doc's folder of
        aniseed_toolkit
        """
        aniseed_toolkit.run(
            "Generate Aniseed Toolkit Api Documentation",
            filepath=aniseed_toolkit.resources.get("docs/tool_api_docs.md"),
        )


class DocumentationGenerator(aniseed_toolkit.Tool):

    identifier = "Generate Aniseed Toolkit Api Documentation"
    user_facing = False

    @classmethod
    def get_plugins(cls, category=None):
        results = []
        for plugin in sorted(aniseed_toolkit.tools.plugins(), key=lambda x: x.identifier):
            if category and category not in plugin.categories:
                continue
            results.append(plugin)
        return results

    @classmethod
    def get_categories(cls):
        return sorted(aniseed_toolkit.tools.categories())

    def run(self, filepath: str = "") -> None:
        """
        This will generate a markdown file for all the tools in the aniseed toolkit

        Args:
            filepath: Where to write the markdown file
        """
        lines = []

        category_header = "#"
        tool_header = "###"
        tool_subheader = "####"

        # -- Create the table of contents
        lines.append(f"{category_header} Table of Contents")
        for category in self.get_categories():
            lines.append(f"- [{category}](#{category})")
            for tool in self.get_plugins(category):
                hyperlink = tool.identifier.replace(" ", "-")
                lines.append(f"  - [`{tool.identifier}`](#{hyperlink})")

        for category in self.get_categories():
            lines.append(f"{category_header} {category.title()}")

            for tool in self.get_plugins(category):

                lines.append("-" * 20)
                lines.append(f"{tool_header} {tool.identifier}")
                lines.append(f"Identifier : `{tool.identifier}`")

                # -- Get the signature
                kwargs = aniseed_toolkit.tools.signature(tool.identifier)

                documentation = tool.run.__doc__

                in_args = False
                in_return = False

                overview = ""
                return_string = ""
                arguments = []

                for line in documentation.split("\n"):

                    if not line.strip():
                        continue

                    if not in_args and "Args:" in line:
                        in_args = True
                        continue

                    if not in_return and "Returns:" in line:
                        in_return = True
                        continue

                    if in_return:
                        return_string = "- " + line.strip()
                        break

                    if in_args:
                        # -- We're parsing a new argument
                        if ":" in line:
                            argument_name = line.split(": ")[0].strip()
                            arg_type = kwargs.get(argument_name, None)
                            if arg_type is None:
                                arg_type = ""
                            else:
                                arg_type = f"(*{str(type(arg_type))}*)"
                                arg_type = arg_type.replace("<class '", "")
                                arg_type = arg_type.replace("'>", "")

                            new_arg = "".join(
                                [
                                    "- `",
                                    argument_name,
                                    "`",
                                    arg_type,
                                    ": ",
                                    line.split(": ")[-1].strip()
                                ]
                            )
                            arguments.append(new_arg)
                            continue

                        # -- We need to append to the last argument
                        arguments[-1] += " " + line.strip()
                        continue


                    overview += " " + line.strip()

                lines.append(f"{tool_subheader} Overview")
                lines.append(overview)
                lines.append(f"{tool_subheader} Args")
                lines.extend(arguments)
                lines.append(f"{tool_subheader} Returns")
                lines.append(return_string)

            with open(filepath, "w") as f:
                for line in lines:
                    f.write(line)
                    f.write("\n\n")
