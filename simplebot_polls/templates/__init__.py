from jinja2 import Environment, PackageLoader, select_autoescape

env = Environment(
    loader=PackageLoader(__name__.split(".")[0], "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)
template = env.get_template("poll.html")
