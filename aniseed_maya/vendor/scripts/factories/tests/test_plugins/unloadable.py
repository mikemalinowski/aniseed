from factories.examples.reader import ReaderPlugin

# -- Add some invalid syntax to demonstrate an unloadable file
ReaderPlugin.FooBar()
