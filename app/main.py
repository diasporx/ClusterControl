import cmd
import psycopg2
import paramiko
import prettytable
import random
import string
from tqdm import tqdm
from colorama import Fore, Style

class MyPrompt(cmd.Cmd):
    intro = Fore.GREEN + '''
    ******************************************
    **                                      **
    **           ClusterControl             **
    **                                      **
    ******************************************

    Welcome to ClusterControl!\n This application allows you to manage and monitor your database clusters. Use the 'help' command to see a list of available commands.\n You can also use the 'help <command>' command to get more information about a specific command.

    Let's get started!
    ''' + Style.RESET_ALL
    prompt = 'ClusterControl_> '

    def __init__(self):
        super().__init__()
        self.conn = psycopg2.connect("dbname=clustercontrol user=postgres password=test host=localhost port=5433")
        self.cur = self.conn.cursor()

    def do_add_server(self, arg):
        '''
        Add a new server to the list of managed servers
        '''
        # Set defaults
        ssh_type = 'ssh'
        ssh_user = 'root'

        # Get user input
        ssh_ip = input('ip: ')
        if not ssh_ip:
            print('ip cannot be empty')
            return
        user_input = input(f'ssh ({ssh_type}): ')
        if user_input:
            ssh_type = user_input
        user_input = input(f'user ({ssh_user}): ')
        if user_input:
            ssh_user = user_input
        user_input = input(f'password_ssh: ')
        if user_input:
            ssh_password = user_input
        user_input = input(f'comment: ')
        if user_input:
            comment = user_input

        # Generate quid
        quid = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # установка соединения по ssh
            with tqdm(total=100, desc='Connecting to server', unit='%') as pbar:
                ssh.connect(ssh_ip, username=ssh_user, password=ssh_password)
                pbar.update(100)

            # добавление сервера в базу данных
            with tqdm(total=100, desc='Adding server to database', unit='%') as pbar:
                self.cur.execute("INSERT INTO servers (connection_command, ssh_ip, ssh_user, ssh_password, comment, quid) VALUES (%s, %s, %s, %s, %s, %s)", (ssh_type, ssh_ip, ssh_user, ssh_password, comment, quid))
                self.conn.commit()
                pbar.update(100)

            print(f'Server {ssh_ip} added successfully with quid {quid}')
        except Exception as e:
            print(f'Error adding server to database: {e}')
            return



    def do_list_servers(self, arg):
        'List all servers that are managed by ClusterControl'
        self.cur.execute("SELECT * FROM servers")
        servers = self.cur.fetchall()

        table = prettytable.PrettyTable(['id', 'quid', 'connection_command', 'ssh_password', 'comment', 'ssh_ip', 'ssh_user'])

        for server in servers:
            table.add_row(server)

        print(table)

    def do_install(self, arg):
        'Install a package on all servers in the list'
        package, *server_ips = arg.split()
        command = f"sudo apt-get install {package} -y"
        for server_ip in server_ips:
            self.cur.execute("SELECT ssh_user, ssh_password, ssh_ip FROM servers WHERE ssh_ip = %s", (server_ip,))
            ssh_user, ssh_password, ssh_ip = self.cur.fetchone()
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ssh_ip, username=ssh_user, password=ssh_password)
            stdin, stdout, stderr = ssh.exec_command(command)
            print(f"Installation output for {ssh_ip}:")
            print(stdout.read().decode())
            ssh.close()

if __name__ == '__main__':
    MyPrompt().cmdloop()