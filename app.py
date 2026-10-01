from blog import create_app

app = create_app()

if __name__ == '__main__':
    # debug mode is controlled by the FLASK_DEBUG environment variable
    app.run()
