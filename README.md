# Chat App using React, Flask, and Sockets

This is a full-stack chat application built with a React frontend, a Flask backend, and Socket.IO for real-time communication.

---

## Features

* **Real-time Messaging**: Instantaneous message delivery between users.
* **Group Chat**: Create and participate in group conversations.
* **User Authentication**: Secure user login and registration.
* **User Profiles**: View and update user profiles with avatars.
* **Online Status**: See which users are currently online.
* **Typing Indicators**: Know when someone is typing a message.
* **Read Receipts**: See when your messages have been read.
* **Dark Mode**: Switch between light and dark themes for comfortable viewing.
* **Search**: Easily find users and conversations.

---

## Technologies Used

### Backend

* **Flask**: A lightweight Python web framework.
* **Flask-SocketIO**: For real-time communication between the client and server.
* **MySQL**: A popular open-source relational database.
* **SQLAlchemy**: A SQL toolkit and Object-Relational Mapper (ORM) for Python.
* **Gunicorn**: A Python WSGI HTTP Server for UNIX.

### Frontend

* **React**: A JavaScript library for building user interfaces.
* **React Router**: For handling routing in the application.
* **Socket.IO Client**: The client-side library for Socket.IO.
* **Tailwind CSS**: A utility-first CSS framework for rapid UI development.
* **Axios**: A promise-based HTTP client for the browser and Node.js.

---

## How to Run This Project

### Prerequisites

* Node.js and npm (or yarn) installed
* Python and pip installed
* MySQL server running

### Backend Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/tarun0648/chatapp-using-react-flask-sockets-i.git](https://github.com/tarun0648/chatapp-using-react-flask-sockets-i.git)
    cd chatapp-using-react-flask-sockets-i/chat-backend
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up the database:**

    This section provides a detailed guide on setting up your MySQL database.

    #### Step 1: Open the MySQL Command-Line Client

    First, open a terminal or command prompt and connect to your MySQL server.

    ```bash
    mysql -u your_username -p
    ```

    Replace `your_username` with your MySQL username. You will be prompted for your password.

    #### Step 2: Create a New Database

    In the MySQL shell, create the `chat_app` database.

    ```sql
    CREATE DATABASE chat_app;
    ```

    You should see a `Query OK` message.

    #### Step 3: Select the Database

    Use the `USE` command to select the newly created database.

    ```sql
    USE chat_app;
    ```

    You will see a `Database changed` message.

    #### Step 4: Import the Database Schema

    Now, import the `database_schema.sql` file. You can do this from within the MySQL shell:

    ```sql
    source /path/to/your/database_schema.sql;
    ```

    **Important:** Replace `/path/to/your/database_schema.sql` with the absolute path to the `database_schema.sql` file on your system.

    Alternatively, you can run the import command directly from your system's terminal (without logging into the MySQL shell):

    ```bash
    mysql -u your_username -p chat_app < /path/to/your/database_schema.sql
    ```

5.  **Configure environment variables:**
    * Create a `.env` file in the `chat-backend` directory.
    * Add the following variables to the `.env` file, replacing the placeholder values with your own:
        ```
        MYSQL_HOST=localhost
        MYSQL_USER=<your_mysql_user>
        MYSQL_PASSWORD=<your_mysql_password>
        MYSQL_DB=chat_app
        SECRET_KEY=<your_secret_key>
        UPLOAD_FOLDER=static/uploads
        ```

6.  **Run the backend server:**
    ```bash
    flask run
    ```
    The backend will be running at `http://localhost:5000`.

### Frontend Setup

1.  **Navigate to the frontend directory:**
    ```bash
    cd ../chat-frontend
    ```

2.  **Install the dependencies:**
    ```bash
    npm install
    ```

3.  **Run the frontend development server:**
    ```bash
    npm start
    ```
    The frontend will be running at `http://localhost:3000`.

4.  **Open your browser** and navigate to `http://localhost:3000` to use the application.
