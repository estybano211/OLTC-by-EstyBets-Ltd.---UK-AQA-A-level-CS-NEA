_C4='log_frame'
_C3='— SHOWDOWN —'
_C2='thinking_fg'
_C1='thinking_bg'
_C0='Enter starting balance (£):'
_B_='Return to Menu'
_Bz='Back to Game Menu'
_By='Leaderboard'
_Bx='Exit Casino'
_Bw='Account Information'
_Bv='Game Menu'
_Bu='Eliminate all opponents'
_Bt='last_man_blind'
_Bs='survive_rounds'
_Br='Temporary Guest Account'
_Bq='Register Account'
_Bp='Username already exists.'
_Bo='No username provided.'
_Bn='termination_reason'
_Bm='terminated_at'
_Bl='Account Status'
_Bk='created_at'
_Bj='registered'
_Bi='User ID and Username do not match.'
_Bh='Confirm Delete'
_Bg='Back to Main Menu'
_Bf='User Management'
_Be='Database Management'
_Bd='Access Casino'
_Bc='Incorrect password'
_Bb='Please load an AES key first.'
_Ba='PEM files'
_BZ='Encryption Software'
_BY='\n                    SELECT 1 FROM user_poker_data WHERE user_id = ?\n                    '
_BX='user_poker_actions'
_BW='user_poker_data'
_BV='admin_logs'
_BU='%(message)s'
_BT='balance_label'
_BS='tournament_fg'
_BR='tournament_bg'
_BQ='tournament_won'
_BP='tournament_over'
_BO='difficulty'
_BN='tie_fg'
_BM='tie_bg'
_BL='blackjack'
_BK='groove'
_BJ='Game Settings'
_BI="Harrogate Hold 'Em"
_BH='eliminate_all'
_BG='write'
_BF='No input provided.'
_BE='Enter Username'
_BD='Incorrect password. Operation cancelled.'
_BC='Please enter Master Password to continue:'
_BB='Verification'
_BA='terms_and_conditions'
_B9='title'
_B8='total_bets'
_B7='bottom_left_bg'
_B6='message'
_B5='23456789TJQKA'
_B4='Balance Depleted'
_B3='center'
_B2='loss_fg'
_B1='loss_bg'
_B0='win_fg'
_A_='win_bg'
_Az='log_fg'
_Ay='log_bg'
_Ax='bottom_right_bg'
_Aw='left_bg'
_Av='rounds_survived'
_Au='earn_target'
_At='win_criteria'
_As='Account Type'
_Ar='User ID must be numeric.'
_Aq='readonly'
_Ap='Cancelled'
_Ao='Submit'
_An='WM_DELETE_WINDOW'
_Am='Exit'
_Al='%d-%m-%Y | %H:%M:%S'
_Ak='action'
_Aj='position'
_Ai='turn'
_Ah='river'
_Ag='Current Bet: £0'
_Af='User not found in database.'
_Ae='#ffffff'
_Ad='win_criteria_target'
_Ac='tournament_players'
_Ab='tournament_rounds'
_Aa='bot_balance'
_AZ='Active'
_AY='terminated'
_AX='Registered'
_AW='vertical'
_AV='-fullscreen'
_AU='password'
_AT='confirmed'
_AS='*.*'
_AR='All files'
_AQ='player_range'
_AP='password_hash'
_AO='showdown'
_AN='flop'
_AM='start_fg'
_AL='start_bg'
_AK='text_bg'
_AJ='top_right_bg'
_AI='endless_mode'
_AH='gauntlet_mode'
_AG='bot_difficulty'
_AF='big_blind'
_AE='small_blind'
_AD='User not found.'
_AC='Warning'
_AB='subheading'
_AA='endless_high_score'
_A9='gauntlet_max_rounds'
_A8='left_fg'
_A7='poker'
_A6='gauntlet_start_difficulty'
_A5='Not Found'
_A4='right'
_A3='call_when_weak'
_A2='fold_to_raise'
_A1='Waiting'
_A0='preflop'
_z='sunken'
_y='<Configure>'
_x='fold'
_w='avg_bet_size'
_v='Administrator'
_u='Decided'
_t='nsew'
_s='tournament_mode'
_r='*'
_q='top_left_bg'
_p='model'
_o='hand2'
_n='s'
_m='bot_count'
_l='verified'
_k='normal'
_j='cards'
_i='Folded'
_h='raise'
_g='Back'
_f='middle_right_bg'
_e='flat'
_d='call'
_c='Success'
_b='both'
_a='rounds_played'
_Z='administrator'
_Y='widget_bg'
_X='emphasis'
_W='disabled'
_V=.0
_U=1.
_T='OUT'
_S='is_bot'
_R='bet'
_Q='player'
_P='heading'
_O='text_fg'
_N='status'
_M='left'
_L='Error'
_K='username'
_J='user_id'
_I='found'
_H='balance'
_G='w'
_F='x'
_E='button'
_D='text'
_C=None
_B=False
_A=True
import sys,os,sqlite3,pandas as pd,json
from datetime import datetime
import logging
from queue import Queue,Empty
import threading
from threading import Thread,Event
from typing import cast
from tkinter import BOTH,BOTTOM,BooleanVar,Button,Canvas,Checkbutton,DISABLED,END,Entry,Frame,filedialog,font,HORIZONTAL,IntVar,Label,messagebox,NORMAL,Scale,Scrollbar,scrolledtext,simpledialog,Spinbox,StringVar,Tk,Toplevel,WORD,X
from tkinter.ttk import Combobox,Treeview
from Crypto.Cipher import AES,PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
import hashlib,hmac,binascii
from treys import Card as TreysCard,Deck as TreysDeck,Evaluator
import random
from itertools import combinations
if getattr(sys,'frozen',_B):BASE_DIR=os.path.dirname(sys.executable)
else:BASE_DIR=os.path.dirname(os.path.abspath(__file__))
DB_FILE=os.path.join(BASE_DIR,'OMTC_database.db')
class DatabaseLogHandler(logging.Handler):
	def __init__(A):super().__init__();A.DB_FILE=DB_FILE;A.queue=Queue();A.stop_event=Event();A.worker_thread=Thread(target=A.processor,daemon=_A);A.worker_thread.start()
	def emit(A,record):
		B=record
		try:C=A.format(B);D=B.levelname;E=datetime.now().strftime(_Al);A.queue.put((E,D,C))
		except Exception:A.handleError(B)
	def processor(A):
		while not A.stop_event.is_set():
			try:
				C,D,E=A.queue.get(timeout=1)
				with sqlite3.connect(A.DB_FILE,timeout=5)as B:B.execute('\n                        INSERT INTO db_logs(timestamp, level, log_entry)\n                        VALUES (?, ?, ?)\n                        ',(C,D,E));B.commit()
				A.queue.task_done()
			except Exception:pass
	def close(A):A.stop_event.set();A.worker_thread.join();super().close()
database_logger=logging.getLogger('omtc_db')
database_logger.setLevel(logging.DEBUG)
if not database_logger.handlers:db_handler=DatabaseLogHandler();db_handler.setLevel(logging.DEBUG);db_formatter=logging.Formatter(_BU);db_handler.setFormatter(db_formatter);database_logger.addHandler(db_handler)
def fetch_database_logger():return database_logger
class AdminLogHandler(logging.Handler):
	def __init__(A):super().__init__();A.DB_FILE=DB_FILE;A.queue=Queue();A.stop_event=Event();A.worker_thread=Thread(target=A.processor,daemon=_A);A.worker_thread.start()
	def emit(A,record):
		B=record
		try:C=A.format(B);D=B.levelname;E=datetime.now().strftime(_Al);A.queue.put((E,D,C))
		except Exception:A.handleError(B)
	def processor(A):
		while not A.stop_event.is_set():
			try:
				C,D,E=A.queue.get(timeout=1)
				with sqlite3.connect(A.DB_FILE,timeout=5)as B:B.execute('\n                        INSERT INTO admin_logs(timestamp, level, log_entry)\n                        VALUES (?, ?, ?)',(C,D,E));B.commit()
				A.queue.task_done()
			except Exception:pass
	def close(A):A.stop_event.set();A.worker_thread.join();super().close()
admin_logger=logging.getLogger('omtc_admin')
admin_logger.setLevel(logging.DEBUG)
if not admin_logger.handlers:admin_handler=AdminLogHandler();admin_handler.setLevel(logging.DEBUG);admin_formatter=logging.Formatter(_BU);admin_handler.setFormatter(admin_formatter);admin_logger.addHandler(admin_handler)
class DatabaseManagement:
	def __init__(A):A.DB_FILE=DB_FILE
	def check_database_exists(A):B=os.path.dirname(os.path.abspath(__file__));C=os.path.join(B,os.path.basename(A.DB_FILE));return os.path.exists(C)
	SCHEMA={'db_logs':'\n        CREATE TABLE IF NOT EXISTS db_logs(\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            timestamp TEXT,\n            level TEXT,\n            log_entry TEXT\n        )  \n        ',_BV:'\n        CREATE TABLE IF NOT EXISTS admin_logs(\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            timestamp TEXT,\n            level TEXT NOT NULL,\n            log_entry TEXT\n        )\n        ','users':'\n        CREATE TABLE IF NOT EXISTS users(\n            user_id INTEGER PRIMARY KEY AUTOINCREMENT,\n            username TEXT UNIQUE NOT NULL,\n            password_hash TEXT,\n            registered INTEGER,\n            balance REAL DEFAULT 10000 CHECK (balance >= 0),\n            created_at TEXT DEFAULT CURRENT_TIMESTAMP,\n            terminated INTEGER DEFAULT 0,\n            terminated_at TEXT,\n            termination_reason TEXT\n        )\n        ',_BW:'\n        CREATE TABLE IF NOT EXISTS user_poker_data(\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            user_id INTEGER,\n            rounds_played INTEGER DEFAULT 0,\n            player_range TEXT,\n            vpip REAL DEFAULT 0,\n            pfr REAL DEFAULT 0,\n            total_hands_played INTEGER DEFAULT 0,\n            total_hands_raised INTEGER DEFAULT 0,\n            total_bets INTEGER DEFAULT 0,\n            fold_to_raise INTEGER DEFAULT 0,\n            call_when_weak INTEGER DEFAULT 0,\n            gauntlet_max_rounds INTEGER DEFAULT 0,\n            endless_high_score INTEGER DEFAULT 0,\n            last_updated TEXT DEFAULT CURRENT_TIMESTAMP,\n            FOREIGN KEY (user_id) REFERENCES users(user_id)\n        )\n        ',_BX:'\n        CREATE TABLE IF NOT EXISTS user_poker_actions(\n            id INTEGER PRIMARY KEY AUTOINCREMENT,\n            user_id INTEGER,\n            round_number INTEGER,\n            street TEXT,\n            action TEXT,\n            bet_size REAL,\n            pot_size REAL,\n            resolved INTEGER DEFAULT 0,\n            created_at TEXT DEFAULT CURRENT_TIMESTAMP,\n            FOREIGN KEY (user_id) REFERENCES users(user_id)\n        )\n        '}
	def connect(B):A=sqlite3.connect(DB_FILE);A.row_factory=sqlite3.Row;A.execute('PRAGMA foreign_keys = ON');return A
	def create_database(A):
		with A.connect()as B:
			try:
				for(C,D)in A.SCHEMA.items():B.execute(D);database_logger.info(f"Table: '{C}' created.")
				B.commit();database_logger.info(f"File: '{DB_FILE}' created.");A.admin_account();database_logger.info("Administrator account added to 'users' table.")
			except sqlite3.Error as E:database_logger.exception(f"'create_database' error. {E}")
	def admin_account(B):
		C='Password1';D=hash_function(C)
		with B.connect()as A:
			try:
				E=A.execute('\n                    SELECT 1 FROM users\n                    WHERE username = ?\n                    ',(_v,))
				if E.fetchone()is _C:A.execute('\n                        INSERT INTO users\n                        (username, password_hash, registered, balance) \n                        VALUES (?, ?, ?, ?)\n                        ',(_v,D,1,_V));database_logger.info('Administrator account created.')
			except sqlite3.Error as F:database_logger.exception(f"'admin_account' error. {F}")
	def admin_logged_in(A):admin_logger.info('Administrator logged in.')
	def admin_accessed_system(A,system):admin_logger.info(f"Administrator accessed system: '{system}'.")
	def change_admin_password(A,new_password):
		with A.connect()as B:
			try:admin_logger.info('Request to change Admin Password.');database_logger.info(f"Request to change Administrator password.");C=hash_function(new_password);B.execute('\n                    UPDATE users \n                    SET password_hash = ? \n                    WHERE username = ?\n                    ',(C,_v));database_logger.info('Administrator password changed.');admin_logger.info('Administrator password change request successful.')
			except sqlite3.Error as D:admin_logger.error('Administrator password change request failed.');database_logger.exception(f"'change_admin_password' error. {D}")
	def view_database(B,table):
		A=table
		if not A:database_logger.error('No table provided for admin_view_database().');return pd.DataFrame()
		with B.connect()as C:
			try:admin_logger.info(f"Request to view Table: '{A}'");database_logger.info(f"Attempting to read data from Table: '{A}'.");D=pd.read_sql_query(f"SELECT * FROM {A}",C);database_logger.info(f"Data from Table: '{A}' read successfully.");admin_logger.info('View table request successful.');return D
			except sqlite3.Error as E:admin_logger.error('View table request failed.');database_logger.exception(f"'view_database' error. {E}");return pd.DataFrame()
	def change_user_record(A,*,user_id,new_username=_C,new_password=_C,new_account_type=_C,new_balance=_C,terminated=_C,reason=_C):
		G=terminated;F=new_balance;E=new_account_type;D=new_password;C=new_username;B=user_id
		if C is not _C:A.change_user_username(B,C)
		if D is not _C:A.change_user_password(B,D)
		if E is not _C:A.change_user_account_type(B,E)
		if F is not _C:A.change_user_balance(B,F)
		if G is not _C:A.change_user_status(B,G,reason)
	def change_user_username(B,user_id,new_username):
		A=user_id
		with B.connect()as C:
			try:admin_logger.info(f"Request to change User ID: '{A}' username.");database_logger.info(f"Request to change User ID: '{A}' username.");C.execute('\n                    UPDATE users\n                    SET username = ?\n                    WHERE user_id = ?\n                    ',(new_username,A));admin_logger.info('Change username request successful.');database_logger.info(f"User username changed.")
			except sqlite3.Error as D:admin_logger.error('Change username request failed.');database_logger.exception(f"'change_user_username' error. {D}")
	def change_user_password(B,user_id,new_password):
		A=user_id
		with B.connect()as C:
			try:admin_logger.info(f"Request to change User: '{A}' password.");database_logger.info(f"Request to change User: '{A}' password.");D=hash_function(new_password);C.execute('\n                    UPDATE users\n                    SET password_hash = ?\n                    WHERE user_id = ?\n                    ',(D,A));admin_logger.info('Change user password request successful.');database_logger.info(f"User password changed.")
			except sqlite3.Error as E:admin_logger.error('Change user password request failed.');database_logger.exception(f"'change_user_password' error. {E}")
	def change_user_account_type(B,user_id,registered):
		A=user_id
		with B.connect()as C:
			try:admin_logger.info(f"Request to change User ID: '{A}' account type.");database_logger.info(f"Request to change User ID: '{A}' account type.");C.execute('\n                    UPDATE users \n                    SET registered = ? \n                    WHERE user_id = ?\n                    ',(registered,A));admin_logger.info('Change user account type request successful.');database_logger.info(f"User account type changed.")
			except sqlite3.Error as D:admin_logger.error('Change user account type request failed.');database_logger.exception(f"'change_user_account_type' error. {D}")
	def change_user_balance(B,user_id,new_balance):
		A=user_id
		with B.connect()as C:
			try:admin_logger.info(f"Request to change User ID: '{A}' balance.");database_logger.info(f"Request to change User ID: '{A}' balance.");C.execute('\n                    UPDATE users \n                    SET balance = ? \n                    WHERE user_id = ?\n                    ',(float(new_balance),A));admin_logger.info('Change user balance request successful.');database_logger.info(f"User balance changed.")
			except sqlite3.Error as D:admin_logger.error('Change user balance request failed.');database_logger.exception(f"'change_user_balance' error. {D}")
	def change_user_status(C,user_id,terminated,reason=_C):
		A=user_id
		with C.connect()as B:
			try:
				D=datetime.now().strftime(_Al);admin_logger.info(f"Request to change User ID: '{A}' status.");database_logger.info(f"Request to change User ID: '{A}' status.")
				if terminated:B.execute('\n                        UPDATE users \n                        SET terminated = 1, terminated_at = ?, termination_reason = ? \n                        WHERE user_id = ?\n                        ',(D,reason,A))
				else:B.execute('\n                        UPDATE users \n                        SET terminated = 0, terminated_at = NULL, termination_reason = NULL \n                        WHERE user_id = ?\n                        ',(A,))
				admin_logger.info('Change user status request successful.');database_logger.info(f"User status changed.")
			except sqlite3.Error as E:admin_logger.error('Change user status request failed.');database_logger.exception(f"'change_user_status' error. {E}")
	def delete_user_record(B,user_id):
		A=user_id
		with B.connect()as C:
			try:admin_logger.info(f"Request to delete User ID: '{A}' record.");database_logger.info(f"Request to delete User ID: '{A}' record.");C.execute('DELETE FROM users WHERE user_id=?',(A,));admin_logger.info('Delete user record request successful.');database_logger.info(f"User record deleted.")
			except sqlite3.Error as D:admin_logger.error('Delete user record request failed.');database_logger.exception(f"'delete_user_record' error. {D}")
	def fetch_user_full_record(F,*,user_id=_C,username=_C):
		B=username;A=user_id
		if A is _C and B is _C:raise ValueError('Either user_id or username must be provided')
		with F.connect()as C:
			try:
				if A is not _C:D=C.execute('SELECT * FROM users WHERE user_id = ?',(A,))
				else:D=C.execute('SELECT * FROM users WHERE username = ?',(B,))
				E=D.fetchone();return dict(E)if E else _C
			except sqlite3.Error as G:database_logger.exception(f"'fetch_user_full_record' error. {G}");return
	def fetch_user_presence(C,username=_C):
		A=username
		with C.connect()as D:
			try:
				database_logger.info(f"Searching for User: '{A}'.");E=D.execute('\n                    SELECT 1 \n                    FROM users \n                    WHERE username = ?\n                    ',(A,));F=E.fetchone();B=F is not _C
				if B:database_logger.info(f"User '{A}' found.")
				else:database_logger.info(f"User '{A}' not found.")
				return{_I:B}
			except sqlite3.Error as G:database_logger.exception(f"'fetch_user_presence' error. {G}");return{_I:_B}
	def sign_in_user(C,username,password,registered):
		B=password;A=username
		if not A or not isinstance(A,str):raise ValueError("'username' must be a non-empty string")
		if A.strip().lower()==_Z:raise ValueError("The username 'Administrator' cannot be used.")
		D=hash_function(B)if B else _C;E=1e4
		with C.connect()as F:
			try:database_logger.info(f"Request to make an account for User: '{A}'.");F.execute('\n                    INSERT INTO users\n                    (username, password_hash, registered, balance) \n                    VALUES (?, ?, ?, ?)\n                    ',(A,D,int(float(registered)),float(E)));database_logger.info(f"Created User: '{A}' record.");return A
			except sqlite3.IntegrityError:database_logger.warning(f"User: '{A}' record already exists.");raise
			except sqlite3.Error as G:database_logger.exception(f"'sign_in_user' error. {G}");raise
	def verify_user_password(D,username,password):
		A=username
		with D.connect()as E:
			try:database_logger.info(f"Request to search for User: '{A}' 'password_hash'.");F=E.execute('\n                    SELECT password_hash \n                    FROM users \n                    WHERE username = ?\n                    ',(A,));B=F.fetchone()
			except sqlite3.Error as G:database_logger.exception(f"'verify_user_password' error. {G}");return{_I:_B,_l:_B}
		if not B or not B[_AP]:database_logger.info(f"'password_hash' for User: '{A}' not found.");return{_I:_B,_l:_B}
		C=verify_hash(B[_AP],password)
		if C:database_logger.info(f"Password verification successful'.")
		else:database_logger.info(f"Failed password attempt.")
		return{_I:_A,_l:C}
	def reset_user_password(B,user_id,new_password):
		A=user_id
		with B.connect()as C:
			try:database_logger.info(f"User request to reset User ID: '{A}' password.");D=hash_function(new_password);C.execute('\n                    UPDATE users \n                    SET password_hash = ? \n                    WHERE user_id = ?\n                    ',(D,A));database_logger.info(f"Password for User reset successfully.")
			except sqlite3.Error as E:database_logger.exception(f"'reset_user_password' error. {E}")
	def fetch_user_id(C,username):
		A=username
		with C.connect()as D:
			try:
				database_logger.info(f"Request to fetch User: '{A}' user_id.");E=D.execute('\n                    SELECT user_id \n                    FROM users \n                    WHERE username = ?\n                    ',(A,));B=E.fetchone()
				if B:database_logger.info(f"User 'user_id' found.");return{_I:_A,_J:B[_J]}
				else:database_logger.info(f"User 'user_id' not found.");return{_I:_B,_J:_C}
			except sqlite3.Error as F:database_logger.exception(f"'fetch_user_id' error. {F}");return{_I:_B,_J:_C}
	def fetch_username(C,user_id):
		A=user_id
		with C.connect()as D:
			try:
				database_logger.info(f"Request to fetch User ID: '{A}' username.");E=D.execute('\n                    SELECT username \n                    FROM users \n                    WHERE user_id = ?\n                    ',(A,));B=E.fetchone()
				if B:database_logger.info(f"User 'username' found.");return{_I:_A,_K:B[_K]}
				else:database_logger.info(f"User 'username' not found.");return{_I:_B,_K:_C}
			except sqlite3.Error as F:database_logger.exception(f"'fetch_username' error. {F}");return{_I:_B,_K:_C}
	def fetch_user_balance(C,username):
		A=username
		with C.connect()as D:
			try:
				database_logger.info(f"Request to fetch User: '{A}' balance.");E=D.execute('\n                    SELECT balance \n                    FROM users \n                    WHERE username = ?\n                    ',(A,));B=E.fetchone()
				if B:database_logger.info(f"User 'balance' found.");return{_I:_A,_H:float(B[_H])}
				else:database_logger.info(f"User 'balance' not found.");return{_I:_B,_H:_V}
			except sqlite3.Error as F:database_logger.exception(f"'fetch_user_balance' error. {F}");return{_I:_B,_H:_V}
	def modify_user_balance(B,username,new_balance):
		A=username
		with B.connect()as C:
			try:database_logger.info(f"Request to modify User: '{A}' balance.");C.execute('\n                    UPDATE users \n                    SET balance = ? \n                    WHERE username = ?\n                    ',(float(new_balance),A));database_logger.info(f"User balance modified.");return
			except sqlite3.Error as D:database_logger.exception(f"'modify_user_balance' error. {D}")
	def terminate_user_account(B,username,reason):
		A=username
		with B.connect()as C:
			try:D=datetime.now().strftime(_Al);database_logger.info(f"Request to terminate User: '{A}' account.");C.execute('\n                    UPDATE users \n                    SET terminated = 1, terminated_at = ?, termination_reason = ? \n                    WHERE username = ?\n                    ',(D,reason,A));database_logger.info(f"User account terminated.");return
			except sqlite3.Error as E:database_logger.exception(f"'terminate_user_account' error. {E}")
	def admin_password_check(C,password):
		with C.connect()as D:
			try:database_logger.info('Request for Administrator password_hash.');E=D.execute('\n                    SELECT password_hash\n                    FROM users \n                    WHERE username = ?\n                    ',(_v,));A=E.fetchone()
			except sqlite3.Error as F:database_logger.exception(f"'admin_password_check' error. {F}");return{_I:_B,_l:_B}
		if not A or not A[_AP]:database_logger.debug("'password_hash' for Administrator not found.");return{_I:_B,_l:_B}
		B=verify_hash(A[_AP],password)
		if B:database_logger.info('Administrator password verification successful.')
		else:database_logger.info('Administrator password verification failed.')
		return{_I:_A,_l:B}
	def check_user_poker_data_exists(C,user_id):
		A=user_id
		with C.connect()as D:
			try:database_logger.info(f"Checking if poker data exists for User ID: '{A}'.");B=D.execute(_BY,(A,)).fetchone();database_logger.info(f"Poker data existence for User: {_I if B else'not found'}.");return B is not _C
			except sqlite3.Error as E:database_logger.exception(f"'check_user_poker_data_exists' error. {E}");return _B
	def initialise_user_poker_data(C,user_id):
		A=user_id
		with C.connect()as B:
			try:
				database_logger.info(f"Initialising poker data for User ID: '{A}'.");D=B.execute(_BY,(A,)).fetchone()
				if D:database_logger.info(f"User poker data already exists");return _A
				B.execute('\n                    INSERT INTO user_poker_data (user_id)\n                    VALUES (?)\n                    ',(A,));B.execute('\n                    UPDATE user_poker_data\n                    SET player_range = ?\n                    WHERE user_id = ?\n                    ',(json.dumps(generate_range_chart()),A));database_logger.info(f"User poker data initialised.");return _A
			except sqlite3.Error as E:database_logger.exception(f"'initialise_user_poker_data' error. {E}");return _B
	def load_user_poker_data(F,user_id):
		B=user_id
		with F.connect()as G:
			try:
				database_logger.info(f"Loading poker data for User ID: '{B}'.");E=G.execute('\n                    SELECT\n                        upd.user_id,\n                        upd.rounds_played,\n                        upd.player_range,\n                        upd.vpip,\n                        upd.pfr,\n                        upd.total_hands_played,\n                        upd.total_hands_raised,\n                        upd.total_bets,\n                        upd.fold_to_raise,\n                        upd.call_when_weak,\n                        upd.last_updated\n                    FROM user_poker_data upd\n                    WHERE upd.user_id = ?\n                    ',(B,)).fetchone()
				if not E:database_logger.warning(f"User not found in poker data");return
				A=dict(E);A[_AQ]=json.loads(A[_AQ])if A.get(_AQ)else _C;H=max(1,A[_a]);A[_w]=A[_B8]/H;C=A[_A2]+A[_A3]
				if C>0:A[_A2]=A[_A2]/C;A[_A3]=A[_A3]/C
				else:A[_A2]=.5;A[_A3]=.5
				database_logger.info(f"Poker data for User ID: '{B}' loaded successfully.");return A
			except sqlite3.Error as D:database_logger.exception(f"'load_user_poker_data' error. {D}");return
			except json.JSONDecodeError as D:database_logger.exception(f"'load_user_poker_data' error. {D}");return
	def update_player_range(B,user_id,player_range):
		A=user_id
		with B.connect()as C:
			try:database_logger.info(f"Updating player range for User ID: '{A}'.");D=json.dumps(player_range);C.execute('\n                    UPDATE user_poker_data\n                    SET \n                        player_range = ?,\n                        last_updated = CURRENT_TIMESTAMP\n                    WHERE user_id = ?\n                    ',(D,A));database_logger.info(f"User player range updated.");return _A
			except(sqlite3.Error,json.JSONDecodeError)as E:database_logger.exception(f"'update_player_range' error. {E}");return _B
	def log_player_action(B,*,user_id,round_number,street,action,bet_size,pot_size):
		A=user_id
		with B.connect()as C:
			try:database_logger.info(f"Logging action for User ID: '{A}'.");C.execute('\n                    INSERT INTO user_poker_actions(\n                        user_id,\n                        round_number,\n                        street,\n                        action,\n                        bet_size,\n                        pot_size\n                    )\n                    VALUES (?, ?, ?, ?, ?, ?)\n                    ',(A,round_number,street,action,bet_size,pot_size));database_logger.info(f"Action logged for User.");return _A
			except sqlite3.Error as D:database_logger.exception(f"'log_player_action' error. {D}");return _B
	def fetch_unresolved_player_actions(C,user_id):
		A=user_id
		with C.connect()as D:
			try:database_logger.info(f"Fetching unresolved actions for User ID: '{A}'.");B=D.execute('\n                    SELECT\n                        id,\n                        user_id,\n                        round_number,\n                        street,\n                        action,\n                        bet_size,\n                        pot_size,\n                        created_at\n                    FROM user_poker_actions\n                    WHERE user_id = ?\n                    AND resolved = 0\n                    ORDER BY round_number ASC, created_at ASC\n                    ',(A,)).fetchall();database_logger.info(f"Fetched {len(B)} unresolved actions for User.");return[dict(A)for A in B]
			except sqlite3.Error as E:database_logger.exception(f"'fetch_unresolved_player_actions' error. {E}");return[]
	def resolve_player_actions(B,user_id,round_number):
		A=user_id
		with B.connect()as C:
			try:database_logger.info(f"Resolving actions for User ID: '{A}'.");C.execute('\n                    UPDATE user_poker_actions\n                    SET resolved = 1\n                    WHERE user_id = ?\n                    AND round_number = ?\n                    ',(A,round_number));database_logger.info(f"User actions resolved.");return _A
			except sqlite3.Error as D:database_logger.exception(f"'resolve_player_actions' error. {D}");return _B
	def update_hand_statistics(B,*,user_id,action,bet_size,pot_size,voluntarily_entered,preflop_raised,faced_raise):
		D=faced_raise;C=action;A=user_id
		with B.connect()as E:
			try:database_logger.info(f"Updating hand statistics for User ID: '{A}'.");E.execute('\n                    UPDATE user_poker_data\n                    SET\n                        rounds_played = rounds_played + 1,\n                        total_hands_played = total_hands_played + ?,\n                        total_hands_raised = total_hands_raised + ?,\n                        total_bets = total_bets + ?,\n                        fold_to_raise = fold_to_raise + ?,\n                        call_when_weak = call_when_weak + ?,\n                        last_updated = CURRENT_TIMESTAMP\n                    WHERE user_id = ?\n                    ',(int(voluntarily_entered),int(preflop_raised),bet_size,int(D and C==_x),int(D and C==_d),A));B.recalculate_frequencies(E,A);database_logger.info(f"User hand statistics updated.");return _A
			except sqlite3.Error as F:database_logger.exception(f"'update_hand_statistics' error. {F}");return _B
	def recalculate_frequencies(G,conn,user_id):
		B=user_id
		try:
			database_logger.info(f"Recalculating frequencies for User ID: '{B}'.");A=conn.execute('\n                SELECT\n                    rounds_played,\n                    total_hands_played,\n                    total_hands_raised\n                FROM user_poker_data\n                WHERE user_id = ?\n                ',(B,)).fetchone()
			if not A or A[_a]==0:return
			C=A[_a];D=A['total_hands_played']/C*1e2;E=A['total_hands_raised']/C*1e2;conn.execute('\n                UPDATE user_poker_data\n                SET vpip = ?, pfr = ?\n                WHERE user_id = ?\n                ',(D,E,B));database_logger.info(f"User frequencies recalculated.")
		except sqlite3.Error as F:database_logger.exception(f"'recalculate_frequencies' error. {F}")
	def fetch_player_statistics(D,user_id):
		B=user_id
		with D.connect()as E:
			try:
				database_logger.info(f"Fetching player statistics for User ID: '{B}'.");C=E.execute('\n                    SELECT\n                        user_id,\n                        rounds_played,\n                        vpip,\n                        pfr,\n                        total_bets,\n                        fold_to_raise,\n                        call_when_weak\n                    FROM user_poker_data\n                    WHERE user_id = ?\n                ',(B,)).fetchone()
				if not C:return
				A=dict(C);F=max(1,A[_a]);A[_w]=A[_B8]/F;database_logger.info(f"User player statistics fetched.");return A
			except sqlite3.Error as G:database_logger.exception(f"'fetch_player_statistics' error. {G}");return
	def fetch_hand_history(D,user_id,limit=50,resolved_only=_A):
		B=user_id
		with D.connect()as E:
			try:
				database_logger.info(f"Fetching hand history for User ID: '{B}'.");A='\n                    SELECT\n                        round_number,\n                        street,\n                        action,\n                        bet_size,\n                        pot_size,\n                        resolved,\n                        created_at\n                    FROM user_poker_actions\n                    WHERE user_id = ?\n                    '
				if resolved_only:A+=' AND resolved = 1'
				A+=' ORDER BY created_at DESC LIMIT ?';C=E.execute(A,(B,limit)).fetchall();database_logger.info(f"Fetched {len(C)} hand history records for User.");return[dict(A)for A in C]
			except sqlite3.Error as F:database_logger.exception(f"'fetch_hand_history' error. {F}");return[]
	def fetch_all_players_data(C):
		with C.connect()as D:
			try:
				database_logger.info('Fetching poker data for all players.');E=D.execute('\n                    SELECT\n                        user_id,\n                        rounds_played,\n                        vpip,\n                        pfr,\n                        total_bets\n                    FROM user_poker_data\n                    WHERE rounds_played > 0\n                    ORDER BY rounds_played DESC\n                    ').fetchall();B=[]
				for F in E:A=dict(F);G=max(1,A[_a]);A[_w]=A[_B8]/G;B.append(A)
				database_logger.info(f"Fetched data for {len(B)} players.");return B
			except sqlite3.Error as H:database_logger.exception(f"'fetch_all_players_data' error. {H}");return[]
	def reset_player_statistics(D,user_id,keep_range=_A):
		B=keep_range;A=user_id
		with D.connect()as C:
			try:
				database_logger.info(f"Resetting player statistics for User ID: '{A}'. Keep range: {B}")
				if B:C.execute('\n                        UPDATE user_poker_data\n                        SET\n                            rounds_played = 0,\n                            vpip = 0,\n                            pfr = 0,\n                            total_hands_played = 0,\n                            total_hands_raised = 0,\n                            total_bets = 0,\n                            fold_to_raise = 0,\n                            call_when_weak = 0,\n                            last_updated = CURRENT_TIMESTAMP\n                        WHERE user_id = ?\n                        ',(A,))
				else:C.execute('\n                        UPDATE user_poker_data\n                        SET\n                            rounds_played = 0,\n                            player_range = NULL,\n                            vpip = 0,\n                            pfr = 0,\n                            total_hands_played = 0,\n                            total_hands_raised = 0,\n                            total_bets = 0,\n                            fold_to_raise = 0,\n                            call_when_weak = 0,\n                            last_updated = CURRENT_TIMESTAMP\n                        WHERE user_id = ?\n                        ',(A,))
				database_logger.info(f"User statistics reset.");return _A
			except sqlite3.Error as E:database_logger.exception(f"'reset_player_statistics' error. {E}");return _B
	def fetch_special_mode_scores(C,user_id):
		A=user_id
		with C.connect()as D:
			try:
				database_logger.info(f"Fetching special-mode scores for User ID: '{A}'.");B=D.execute('\n                    SELECT gauntlet_max_rounds, endless_high_score\n                    FROM   user_poker_data\n                    WHERE  user_id = ?\n                    ',(A,)).fetchone()
				if not B:database_logger.info(f"No special-mode scores found for user_id {A}.");return
				database_logger.info(f"User special-mode scores fetched.");return{_A9:int(B[_A9]or 0),_AA:int(B[_AA]or 0)}
			except sqlite3.Error as E:database_logger.exception(f"'fetch_special_mode_scores' error. {E}");return
	def update_special_mode_score(D,user_id,column,new_score):
		B=new_score;A=column;C={_A9,_AA}
		if A not in C:raise ValueError(f"column must be one of {C}, got {A!r}")
		with D.connect()as E:
			try:E.execute(f"""
                    UPDATE user_poker_data
                    SET {A} = ?,
                    last_updated = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    AND {A} < ?
                    """,(B,user_id,B));database_logger.info(f"Updated {A} to {B}");return _A
			except sqlite3.Error as F:database_logger.exception(f"'update_special_mode_score' error. {F}");return _B
def fetch_font_settings(root):C='Helvetica';B='bold';A=root;D={_B9:font.Font(root=A,family='Times New Roman',size=35,weight=B,underline=_A),_P:font.Font(root=A,family='Arial',size=28,weight=B,underline=_A),_AB:font.Font(root=A,family=C,size=24,weight=B),_D:font.Font(root=A,family='Verdana',size=20),_E:font.Font(root=A,family='Tahoma',size=18,weight=B),_BA:font.Font(root=A,family=C,size=20,weight=B),_X:font.Font(root=A,family='Georgia',size=12,weight=B,slant='italic')};return D
DELAY=1.5
def clear_current_section(self):
	A=self
	if getattr(A,'current_section_frame',_C)is not _C:A.current_section_frame.destroy();A.current_section_frame=_C
def set_view(self,view_builder):A=self;clear_current_section(A);A.current_section_frame=Frame(A.main_frame);A.current_section_frame.pack(expand=_A,fill=_b);view_builder(A.current_section_frame)
class Encryption_Software:
	def __init__(A):
		A.enc_soft_root=Tk();A.enc_soft_root.title('One More Time Casino - Encryption Software');A.styles=fetch_font_settings(A.enc_soft_root)
		try:A.dbm=DatabaseManagement();A.dbm.admin_accessed_system(_BZ)
		except:pass
		A.aes_key=_C;A.main_frame=Frame(A.enc_soft_root);A.main_frame.pack(expand=_A,fill=_b,padx=20,pady=20);A.current_section_frame=_C;set_view(A,A.create_main_interface);A.enc_soft_root.mainloop()
	def create_main_interface(A,frame):
		B=frame;Label(B,text=_BZ,font=A.styles[_P]).pack(pady=10);C=[('Generate RSA Keypair',A.generate_rsa_keys),('Generate & Encrypt AES Key',A.generate_encrypted_aes_key),('Load Encrypted AES Key',A.load_rsa_aes_key),('Encrypt File',A.encrypt_file),('Decrypt File',A.decrypt_file),(_Am,A.enc_soft_root.destroy)]
		for(D,E)in C:Button(B,text=D,font=A.styles[_E],width=40,command=E).pack(pady=5)
	def generate_rsa_keys(J):
		A=filedialog.askdirectory(title='Select folder to save RSA keys')
		if not A:return
		try:
			C=RSA.generate(2048);G=C.export_key();H=C.publickey().export_key();D=datetime.now().strftime('%d-%B-%Y');E=os.path.join(A,f"private_key_{D}.pem");F=os.path.join(A,f"public_key_{D}.pem")
			with open(E,'wb')as B:B.write(G)
			with open(F,'wb')as B:B.write(H)
			messagebox.showinfo(_c,f"RSA keys generated and saved:\n{E}\n{F}")
		except Exception as I:messagebox.showerror(_L,f"Failed to generate RSA keys: {I}")
	def generate_encrypted_aes_key(K):
		B=filedialog.askopenfilename(title='Select RSA Public Key',filetypes=[(_Ba,'*.pem'),(_AR,_AS)])
		if not B:return
		C=filedialog.askdirectory(title='Select folder to save encrypted AES key')
		if not C:return
		try:
			E=get_random_bytes(32)
			with open(B,'rb')as A:F=RSA.import_key(A.read())
			G=PKCS1_OAEP.new(F);H=G.encrypt(E);I=datetime.now().strftime('%d-%B-%Y');D=os.path.join(C,f"aes_key_{I}.bin")
			with open(D,'wb')as A:A.write(H)
			messagebox.showinfo(_c,f"Encrypted AES key saved to:\n{D}")
		except Exception as J:messagebox.showerror(_L,f"Failed to generate/encrypt AES key: {J}")
	def load_rsa_aes_key(D):
		B=filedialog.askopenfilename(title='Select RSA Private Key',filetypes=[(_Ba,'*.pem'),(_AR,_AS)])
		if not B:return
		C=filedialog.askopenfilename(title='Select Encrypted AES Key',filetypes=[('Binary files','*.bin'),(_AR,_AS)])
		if not C:return
		try:
			with open(B,'rb')as A:E=RSA.import_key(A.read())
			with open(C,'rb')as A:F=A.read()
			G=PKCS1_OAEP.new(E);D.aes_key=G.decrypt(F);messagebox.showinfo(_c,'AES key loaded successfully.')
		except Exception as H:messagebox.showerror(_L,f"Failed to load AES key: {H}")
	def encrypt_file(C):
		if not C.aes_key:messagebox.showwarning(_AC,_Bb);return
		B=filedialog.askopenfilename(title='Select database to encrypt',filetypes=[('Database files','*.db'),(_AR,_AS)])
		if not B:return
		try:
			with open(B,'rb')as A:F=A.read()
			D=AES.new(C.aes_key,AES.MODE_EAX);G,H=D.encrypt_and_digest(F);E=B+'.enc'
			with open(E,'wb')as A:A.write(D.nonce);A.write(H);A.write(G)
			messagebox.showinfo(_c,f"Database encrypted and saved to:\n{E}")
		except Exception as I:messagebox.showerror(_L,f"Encryption failed: {I}")
	def decrypt_file(C):
		if not C.aes_key:messagebox.showwarning(_AC,_Bb);return
		A=filedialog.askopenfilename(title='Select encrypted database',filetypes=[('Encrypted files','*.enc'),(_AR,_AS)])
		if not A:return
		try:
			with open(A,'rb')as B:E=B.read(16);F=B.read(16);G=B.read()
			H=AES.new(C.aes_key,AES.MODE_EAX,nonce=E);I=H.decrypt_and_verify(G,F);D=A[:-4]if A.endswith('.enc')else A+'.dec'
			with open(D,'wb')as B:B.write(I)
			messagebox.showinfo(_c,f"Database decrypted and saved to:\n{D}")
		except Exception as J:messagebox.showerror(_L,f"Decryption failed: {J}")
PBKDF2_ITERATIONS=200000
SALT_BYTES=16
def hash_function(string):
	A=string
	if not isinstance(A,str):raise TypeError('Input must be a string.')
	B=os.urandom(SALT_BYTES);C=hashlib.pbkdf2_hmac('sha256',A.encode('utf-8'),B,PBKDF2_ITERATIONS);return f"{binascii.hexlify(B).decode()}${binascii.hexlify(C).decode()}"
def verify_hash(stored_string,input_string):
	try:A,B=stored_string.split('$')
	except ValueError:return _B
	C=binascii.unhexlify(A);D=binascii.unhexlify(B);E=hashlib.pbkdf2_hmac('sha256',input_string.encode('utf-8'),C,PBKDF2_ITERATIONS);return hmac.compare_digest(E,D)
def passwords_confirmation(frame,root):
	B=fetch_font_settings(root);C={_AT:_B,_AU:_C};A=Toplevel(frame);A.title('Confirm Password');A.protocol(_An,lambda:_C);Label(A,text='Enter password:',font=B[_D]).pack(pady=5);E=Entry(A,show=_r,width=30,font=B[_D]);E.pack(pady=5);Label(A,text='Confirm password:',font=B[_D]).pack(pady=5);F=Entry(A,show=_r,width=30,font=B[_D]);F.pack(pady=5);G=Label(A,text='',font=B[_X],fg='red');G.pack(pady=5)
	def H():
		B=E.get().strip();D=F.get().strip()
		if B and B==D:C[_AT]=_A;C[_AU]=B;A.destroy()
		else:G.config(text='Passwords do not match or are empty.')
	def I():A.destroy()
	D=Frame(A);D.pack(pady=10);Button(D,text=_Ao,font=B[_E],command=H).pack(side=_M,padx=5);Button(D,text='Cancel',font=B[_E],command=I).pack(side=_M,padx=5);root.wait_window(A);return C
class Admin_Interface:
	def __init__(A,signed_in=_B):
		A.interface_root=Tk();A.interface_root.title('One More Time Casino - Administrator Interface');A.dbm=DatabaseManagement();A.DB_FILE=DB_FILE
		if not A.dbm.check_database_exists():A.dbm.create_database()
		A.styles=fetch_font_settings(A.interface_root);A.main_frame=Frame(A.interface_root);A.main_frame.pack(expand=_A,fill=_b,padx=20,pady=20);A.current_section_frame=_C
		if not signed_in:set_view(A,A.administrative_check)
		else:set_view(A,A.interface_init)
		A.interface_root.mainloop()
	def administrative_check(A,frame):
		B=frame;Label(B,text='Enter Administrator Password:',font=A.styles[_D]).pack(pady=5);C=Entry(B,show=_r,font=A.styles[_D]);C.pack(pady=5)
		def D():
			D=C.get();B=A.dbm.admin_password_check(D)
			if B.get(_I)and B.get(_l):set_view(A,A.interface_init)
			else:messagebox.showerror(_L,_Bc);C.delete(0,'end')
		Button(B,text=_Ao,font=A.styles[_E],command=D).pack(pady=10)
	def interface_init(A,frame):
		B=frame;Label(B,text='Welcome Administrator',font=A.styles[_P]).pack(pady=20);A.dbm.admin_logged_in();C=[('Access Admin Console',A.admin_console),(_Bd,A.access_casino),(_Am,A.interface_root.destroy)]
		for(D,E)in C:Button(B,text=D,font=A.styles[_E],width=30,command=E).pack(pady=3)
	def admin_console(A):Admin_Console()
	def access_casino(A):Casino_Interface(_A)
class Admin_Console:
	def __init__(A):
		A.adm_console_root=Tk();A.adm_console_root.title('One More Time Casino - Administrator Console')
		try:A.adm_console_root.attributes(_AV,_A)
		except Exception:pass
		A.dbm=DatabaseManagement();A.DB_FILE=DB_FILE;A.MASTER_PASSWORD='Master_Password';A.styles=fetch_font_settings(A.adm_console_root);A.main_frame=Frame(A.adm_console_root);A.main_frame.pack(expand=_A,fill=_b,padx=20,pady=20);A.current_section_frame=_C;set_view(A,A.show_console_menu);A.adm_console_root.mainloop()
	def show_console_menu(A,frame):
		B=frame;Label(B,text='Administrative Console',font=A.styles[_P]).pack(pady=(0,20));C=[('Change Administrative Password',lambda:set_view(A,A.change_admin_password)),('Access Encryption Software',A.encryption_software_access),(_Be,lambda:set_view(A,A.show_database_management)),(_Bf,lambda:set_view(A,A.show_user_management)),(_Am,A.adm_console_root.destroy)]
		for(D,E)in C:Button(B,text=D,font=A.styles[_E],width=30,command=E).pack(pady=5)
	def change_admin_password(A,frame):
		B=frame
		if not A.dbm.check_database_exists():messagebox.showwarning(_AC,f"'{A.DB_FILE}' does not exist.");return
		if messagebox.askyesno('Confirm password change',f"Are you sure you want to change the administrative password to the system?"):
			try:
				D=simpledialog.askstring(_BB,_BC,show=_r,parent=A.adm_console_root)
				if D==A.MASTER_PASSWORD:
					Label(B,text='Enter Old Administrator Password:',font=A.styles[_P]).pack(pady=20);C=Entry(B,show=_r,font=A.styles[_D]);C.pack(pady=5)
					def E():
						F=C.get();D=A.dbm.admin_password_check(F)
						if not(D.get(_I)and D.get(_l)):messagebox.showerror(_L,_Bc);C.delete(0,'end');return
						E=passwords_confirmation(B,A.adm_console_root)
						if not E[_AT]:return
						G=E[_AU];A.dbm.change_admin_password(G);messagebox.showinfo(_c,'Administrator password updated successfully!');set_view(A,A.show_console_menu)
					Button(B,text='next',font=A.styles[_E],width=25,command=E).pack(pady=10);Button(B,text=_g,font=A.styles[_E],width=25,command=lambda:set_view(A,A.show_console_menu)).pack(pady=10)
				else:messagebox.showerror(_L,_BD);set_view(A,A.show_console_menu)
			except Exception as F:messagebox.showerror(_L,f": {F}")
		else:messagebox.showinfo(_Ap,'Password change cancelled.');set_view(A,A.show_console_menu)
	def encryption_software_access(A):Encryption_Software()
	def show_database_management(A,frame):
		B=frame;Label(B,text=_Be,font=A.styles[_P]).pack(pady=10);C=[('Create Database',A.create_database),('Delete Database',A.delete_database),('View Database',lambda:set_view(A,A.show_view_database)),(_Bg,lambda:set_view(A,A.show_console_menu))]
		for(D,E)in C:Button(B,text=D,font=A.styles[_E],width=30,command=E).pack(pady=5)
	def create_database(A):
		if messagebox.askyesno('Confirm Creation',f"Are you sure you want to create '{A.DB_FILE}'?\n Note: Nothing will change if the database is already present."):
			try:
				B=simpledialog.askstring(_BB,_BC,show=_r,parent=A.adm_console_root)
				if B==A.MASTER_PASSWORD:A.dbm.create_database();messagebox.showinfo(_c,f"'{A.DB_FILE}' created successfully.")
				else:messagebox.showerror(_L,_BD)
			except Exception as C:messagebox.showerror(_L,f"Failed to create '{A.DB_FILE}': {C}")
	def delete_database(A):
		if not A.dbm.check_database_exists():messagebox.showwarning(_AC,f"'{A.DB_FILE}' does not exist.");return
		if messagebox.askyesno(_Bh,f"Are you sure you want to delete '{A.DB_FILE}'?"):
			try:
				B=simpledialog.askstring(_BB,_BC,show=_r,parent=A.adm_console_root)
				if B==A.MASTER_PASSWORD:os.remove(A.DB_FILE);messagebox.showinfo(_c,f"'{A.DB_FILE}' deleted successfully.")
				else:messagebox.showerror(_L,_BD)
			except Exception as C:messagebox.showerror(_L,f"Failed to delete '{A.DB_FILE}': {C}")
	def show_view_database(A,frame):
		B=frame
		if not A.dbm.check_database_exists():messagebox.showwarning(_AC,f"'{A.DB_FILE}' does not exist.");return
		Label(B,text='Select Table to View',font=A.styles[_P]).pack(pady=10);D=['db_logs',_BV,'users',_BW,_BX];C=Combobox(B,values=D,state=_Aq,font=A.styles[_D]);C.pack(pady=10)
		def E():
			B=C.get().strip()
			if not B:messagebox.showerror(_L,'Please select a table first.');return
			D=A.dbm.view_database(B)
			if D.empty:messagebox.showinfo('Info',f"No data found in '{B}'.");return
			set_view(A,lambda f:A.display_table(f,D,B))
		Button(B,text='View Table',font=A.styles[_E],width=25,command=E).pack(pady=5);Button(B,text=_g,font=A.styles[_E],width=25,command=lambda:set_view(A,A.show_database_management)).pack(pady=5)
	def display_table(C,frame,dataframe,table_name):
		J='oddrow';I='evenrow';F=frame;D=dataframe;Label(F,text=f"'{table_name}' Table",font=C.styles[_P]).pack(pady=10);E=Frame(F);E.pack(expand=_A,fill=_b,padx=10,pady=10);G=Scrollbar(E,orient=_AW);G.pack(side=_A4,fill='y');H=Scrollbar(E,orient='horizontal');H.pack(side='bottom',fill=_F);A=Treeview(E,columns=list(D.columns),show='headings',yscrollcommand=G.set,xscrollcommand=H.set);A.pack(expand=_A,fill=_b);G.config(command=A.yview);H.config(command=A.xview)
		for B in D.columns:A.heading(B,text=B);K=max(D[B].astype(str).map(len).max(),len(B))*10;A.column(B,width=K,anchor=_G)
		for(L,(O,M))in enumerate(D.iterrows()):N=I if L%2==0 else J;A.insert('','end',values=list(M),tags=(N,))
		A.tag_configure(I,background='#a50b5e');A.tag_configure(J,background='#feb29c');Button(F,text=_g,font=C.styles[_E],width=25,command=lambda:set_view(C,C.show_view_database)).pack(pady=5)
	def show_user_management(A,frame):
		B=frame
		if not A.dbm.check_database_exists():messagebox.showwarning(_AC,f"'{A.DB_FILE}' does not exist.");return
		Label(B,text=_Bf,font=A.styles[_P]).pack(pady=10);C=[('Return User Information',lambda:set_view(A,A.fetch_user_record)),('Add User',lambda:set_view(A,A.add_user)),('Edit User',lambda:set_view(A,A.edit_user)),('Delete User',lambda:set_view(A,A.delete_user)),(_Bg,lambda:set_view(A,A.show_console_menu))]
		for(D,E)in C:Button(B,text=D,font=A.styles[_E],width=30,command=E).pack(pady=5)
	def fetch_user_record(A,frame):
		B=frame;Label(B,text='Enter User ID',font=A.styles[_P]).pack(pady=10);D=Entry(B);D.pack(pady=5);Label(B,text=_BE,font=A.styles[_P]).pack(pady=10);E=Entry(B);E.pack(pady=5)
		def C():
			if D.get().strip()and E.get().strip():
				C=D.get().strip();F=E.get().strip()
				if C.isdigit():
					G=A.dbm.fetch_username(int(C));H=A.dbm.fetch_user_id(F)
					if G[_K]!=F or H[_J]!=int(C):messagebox.showerror(_L,_Bi);return
					B=A.dbm.fetch_user_full_record(user_id=int(C))
					if not B:messagebox.showinfo(_A5,_AD);return
				else:messagebox.showerror(_L,_Ar);return
				set_view(A,lambda f:A.display_user_record(f,B))
			elif D.get().strip():
				C=D.get().strip()
				if C.isdigit():
					B=A.dbm.fetch_user_full_record(user_id=int(C))
					if not B:messagebox.showinfo(_A5,_AD);return
				else:messagebox.showerror(_L,_Ar);return
				set_view(A,lambda f:A.display_user_record(f,B))
			elif E.get().strip():
				F=E.get().strip();B=A.dbm.fetch_user_full_record(username=F)
				if not B:messagebox.showinfo(_A5,_AD);return
				set_view(A,lambda f:A.display_user_record(f,B))
			else:messagebox.showerror(_L,_BF);return
		Button(B,text='Search',font=A.styles[_E],width=25,command=C).pack(pady=10);Button(B,text=_g,font=A.styles[_E],width=25,command=lambda:set_view(A,A.show_user_management)).pack(pady=5)
	def display_user_record(B,frame,record):
		C=frame;A=record;Label(C,text=f"User Information: {A.get(_K)}",font=B.styles[_P]).pack(pady=10)
		for(D,E)in[('Username',A[_K]),('Password',A[_AP]),(_As,_AX if A[_Bj]else'Guest'),('Balance',A[_H]),('Creation Time',A[_Bk]),(_Bl,f'Terminated\n At {A[_Bm]}\nBecause "{A[_Bn]}"'if A[_AY]else _AZ)]:Label(C,text=f"{D}: {E}",font=B.styles[_D],anchor=_G).pack(fill=_F,padx=20,pady=2)
		Button(C,text=_g,font=B.styles[_E],width=25,command=lambda:set_view(B,B.show_user_management)).pack(pady=10)
	def add_user(A,frame):
		B=frame;Label(B,text=_BE,font=A.styles[_P]).pack(pady=10);C=Entry(B);C.pack(pady=5)
		def next():
			B=C.get().strip()
			if not B:messagebox.showinfo(_Ap,_Bo);set_view(A,A.show_user_management);return
			if A.dbm.fetch_user_presence(B).get(_I):messagebox.showerror(_L,_Bp);return
			set_view(A,lambda f:A.choose_account_type(f,B))
		Button(B,text='Next',font=A.styles[_E],width=25,command=next).pack(pady=10);Button(B,text=_g,font=A.styles[_E],width=25,command=lambda:set_view(A,A.show_user_management)).pack(pady=5)
	def choose_account_type(A,frame,username):
		C=username;B=frame;Label(B,text=_As,font=A.styles[_P]).pack(pady=10)
		def D():set_view(A,lambda f:A.create_password(f,C))
		def E():A.dbm.sign_in_user(C,_C,_B);messagebox.showinfo(_c,f"Temporary guest account '{C}' created successfully!");set_view(A,A.show_user_management)
		Button(B,text=_Bq,font=A.styles[_E],width=25,command=D).pack(pady=5);Button(B,text=_Br,font=A.styles[_E],width=25,command=E).pack(pady=5);Button(B,text=_g,font=A.styles[_E],width=25,command=lambda:set_view(A,A.show_user_management)).pack(pady=5)
	def create_password(A,frame,username):
		B=username
		while _A:
			C=passwords_confirmation(frame,A.adm_console_root)
			if C[_AT]:A.dbm.sign_in_user(B,C[_AU],_A);messagebox.showinfo(_c,f"Account for '{B}' created successfully!");set_view(A,A.show_user_management);break
	def edit_user(A,frame):
		B=frame;Label(B,text='Enter User ID:',font=A.styles[_P]).pack(pady=10);D=Entry(B);D.pack(pady=5);Label(B,text='Enter Username:',font=A.styles[_P]).pack(pady=10);E=Entry(B);E.pack(pady=5)
		def next():
			if D.get().strip()and E.get().strip():
				C=D.get().strip();F=E.get().strip()
				if C.isdigit():
					G=A.dbm.fetch_username(int(C));H=A.dbm.fetch_user_id(F)
					if G[_K]!=F or H[_J]!=int(C):messagebox.showerror(_L,_Bi);return
					B=A.dbm.fetch_user_full_record(user_id=int(C))
					if not B:messagebox.showinfo(_A5,_AD);return
				else:messagebox.showerror(_L,_Ar);return
				set_view(A,lambda f:A.show_edit_form(f,B))
			elif D.get().strip():
				C=D.get().strip()
				if C.isdigit():
					B=A.dbm.fetch_user_full_record(user_id=int(C))
					if not B:messagebox.showinfo(_A5,_AD);return
				else:messagebox.showerror(_L,_Ar);return
				set_view(A,lambda f:A.show_edit_form(f,B))
			elif E.get().strip():
				F=E.get().strip()
				if not F:messagebox.showerror(_L,_BF);return
				B=A.dbm.fetch_user_full_record(username=F)
				if not B:messagebox.showinfo(_A5,_AD);return
				set_view(A,lambda f:A.show_edit_form(f,B))
			else:messagebox.showerror(_L,_BF);return
		Button(B,text='Next',font=A.styles[_E],width=25,command=next).pack(pady=10);Button(B,text=_g,font=A.styles[_E],width=25,command=lambda:set_view(A,A.show_user_management)).pack(pady=5)
	def show_edit_form(B,frame,record):
		K='Terminated';J='Temporary';C=record;A=frame;Label(A,text=f"Edit User:\n{C[_J]} | {C[_K]}",font=B.styles[_P]).pack(pady=10);Label(A,text='New Username:').pack();D=Entry(A);D.pack();Label(A,text='New Password:').pack();E=Entry(A,show=_r);E.pack();Label(A,text='New Account Type:').pack();F=Combobox(A,values=[_AX,J],state=_Aq);F.set(_AX if not C.get('temporary')else J);F.pack();Label(A,text='New Balance:').pack();G=Entry(A);G.insert(0,str(C.get(_H,0)));G.pack();Label(A,text='Account Status:').pack();H=Combobox(A,values=[_AZ,K],state=_Aq);H.set(_AZ if not C.get(_AY)else K);H.pack();Label(A,text='New Status Reason (if terminated):').pack();I=Entry(A);I.pack()
		def L():
			K='reason';J='new_account_type';A={_J:C[_J]}
			if D.get().strip():A['new_username']=D.get().strip()
			if E.get().strip():A['new_password']=E.get().strip()
			if F.get()==_AX:A[J]=_A
			else:A[J]=_B
			try:A['new_balance']=float(G.get())
			except ValueError:messagebox.showerror(_L,'Invalid balance.');return
			if H.get()==_AZ:A[_AY]=_B;A[K]=_C
			else:
				A[_AY]=_A
				if I.get().strip():A[K]=I.get().strip()
				else:messagebox.showerror(_L,'Status reason required for terminated accounts.');return
			B.dbm.change_user_record(**A);messagebox.showinfo(_c,'User updated successfully.');set_view(B,B.show_user_management)
		Button(A,text='Save Changes',font=B.styles[_E],width=25,command=L).pack(pady=10);Button(A,text=_g,font=B.styles[_E],width=25,command=lambda:set_view(B,B.show_user_management)).pack(pady=5)
	def delete_user(A,frame):
		B=frame;Label(B,text='Enter Username to Delete',font=A.styles[_P]).pack(pady=10);C=Entry(B);C.pack(pady=5)
		def next():
			B=C.get().strip()
			if not B or not A.dbm.fetch_user_presence(B).get(_I):messagebox.showerror(_L,'Username does not exist.');return
			if B==_v:messagebox.showerror(_L,'Cannot delete the Administrator account.');return
			if messagebox.askyesno(_Bh,f"Delete user '{B}'?"):
				D=A.dbm.fetch_user_id(B)
				if D[_I]:A.dbm.delete_user_record(D[_J])
				messagebox.showinfo(_c,f"User '{B}' deleted.");set_view(A,A.show_user_management)
		Button(B,text='Delete',font=A.styles[_E],width=25,command=next).pack(pady=10);Button(B,text=_g,font=A.styles[_E],width=25,command=lambda:set_view(A,A.show_user_management)).pack(pady=5)
def terms_and_conditions():return"\n\n    ---\n\n    **Terms and Conditions for One More Time Casino Ltd**\n\n    ---\n\n    ### © Belongs to ~~~ The composition of this code is original and not to be sold commercially unless stated otherwise by the owner.\n\n    ### Last Updated: 12/09/2025 22:14:55 GMT\n\n    ---\n\n    **INTRODUCTION**\n\n    Welcome to One More Time Casino Ltd (“we,” “us,” or “the Casino”). By accessing or using the services provided by One More Time Casino Ltd (the “Services”) through our future website, future mobile application, or other platforms (collectively referred to as the “Platform”), you agree to comply with and be bound by these Terms and Conditions (“Terms”). These Terms constitute a legally binding agreement between you (“the Player,” “User,” or “you”) and One More Time Casino Ltd. If you do not agree with these Terms, you should refrain from using the Platform or any Services provided by the Casino.\n\n    Please read these Terms carefully before proceeding, as they outline your rights, obligations, and limitations as a Player on One More Time Casino Ltd.\n\n    ---\n\n    ### 1. GENERAL TERMS\n\n    #### 1.1 Eligibility\n\n    1.1.1 Players must be at least 2 months old to access and use the Services of the Casino. By creating an account, you confirm that you meet the minimum requirements and accept all responsibility.\n    1.1.2 The Casino reserves the right to request proof of age and may suspend or terminate your account if appropriate verification is not provided. All funds shall be donated to the CEO's gaming funds.\n\n    #### 1.2 Account Registration\n\n    1.2.1 To access the data servers and hold the right to withdraw any money earned, Players must create a personal account (“Account”). The Player agrees to provide accurate, current, and complete information during the registration process and to update such information as necessary. If an account isn’t created, any money earned during the usage of a temporary account will return to the Casino.\n    1.2.2 Each Player may only create and maintain one account. Multiple accounts for the same Player are prohibited, and the Casino reserves the right to suspend or terminate any duplicate accounts. Please consult Section 9 for further information.\n    1.2.3 Players are responsible for maintaining the confidentiality of their login details. Any activities performed through your account, whether authorised or unauthorised, are your responsibility. You agree to notify the Casino immediately if you suspect any unauthorised use of your Account.\n\n    ---\n\n    ### 2. USE OF THE SERVICES\n\n    #### 2.1 License to Use the Platform\n\n    2.1.1 Upon successful registration, the Casino grants you a limited, non-transferable, and revocable license to use the Platform for personal entertainment purposes only.\n    2.1.2 You agree not to:\n\n    * Use the Platform for any unlawful or fraudulent activity.\n    * Engage in any behaviour that disrupts or negatively impacts the Casino’s reputation, operations or services.\n    * Reverse engineer, modify, or alter any part of the Platform or its software. If caught doing so, punishment Level 3 will be instigated.\n\n    #### 2.2 Prohibited Activities\n\n    2.2.1 Players must refrain from engaging in any activity that violates applicable laws, regulations, or Casino rules. This includes, but is not limited to:\n\n    * Attempting to manipulate or interfere with the proper functioning of the Platform; any damages caused to the database must be paid in full.\n    * Collusion or cheating, including any unauthorised use of software or bots to gain an unfair advantage.\n    * Money laundering or using the Platform as a conduit for illegal financial transactions.\n    * Anything the CEO perceives as unfavourable or detrimental.\n    * Causing emotional distress to the CEO.\n\n    ---\n\n    ### 3. FINANCIAL TRANSACTIONS\n\n    #### 3.1 Deposits\n\n    3.1.1 Players may deposit funds into their Casino Account using payment methods made available by the Casino. The Casino reserves the right to determine which payment methods are accepted, and some methods may only be available based on the Player’s location.\n    3.1.2 All deposits must be made in the Player’s name. Deposits by third parties may be deemed invalid, and the Casino reserves the right to refund or freeze such transactions and use them for the purchase of Pokémon cards.\n    3.1.3 Players are responsible for ensuring that their deposit funds are legitimate. The Casino will not be liable for deposit delays or failures caused by external banking institutions or third-party providers.\n\n    #### 3.2 Withdrawals\n\n    3.2.1 Players may request withdrawals of available funds by following the procedures set out in the Platform. Withdrawals are subject to minimum and maximum limits outlined by the Casino.\n    3.2.2 The Casino may require Players to verify their identity before processing withdrawal requests. Verification may include providing documents such as proof of identity, address, and payment method used. Most of the time a password will suffice.\n    3.2.3 The Casino reserves the right to withhold or delay withdrawals if fraudulent activity is suspected or if wagering requirements tied to bonuses have not been fulfilled.\n    3.2.4 Withdrawals will be processed using the same method as the deposit, where possible, or by an alternative method approved by the Casino.\n    3.2.5 Withdrawals may be received between the next 5 minutes and G years, where G = g64: g1 = 3↑↑↑↑3, gn = 3↑gn−13.\n\n    ---\n\n    ### 4. BONUSES AND PROMOTIONS\n\n    #### 4.1 General Terms for Bonuses\n\n    4.1.1 The Casino may offer bonuses, promotions, or loyalty rewards to Players. Each bonus is subject to specific terms provided at the time of the offer. By accepting a bonus, the Player agrees to comply with its terms.\n    4.1.2 Bonus offers are limited to one per person, household, email address, or IP address unless otherwise stated. Abuse may lead to Section 9, 9.4.\n\n    #### 4.2 Wagering Requirements\n\n    4.2.1 All bonuses are subject to wagering requirements before withdrawal. Wagering requirements refer to the amount a Player must bet before being eligible to withdraw bonus-related winnings.\n    4.2.2 Certain games may contribute differently to fulfilment of wagering requirements. For example, slot games may contribute 100%, while table games like WhiteJoe may contribute a smaller percentage or none at all.\n\n    #### 4.3 Bonus Abuse\n\n    4.3.1 Bonus abuse includes using multiple accounts, colluding to exploit bonuses, or violating specific promotion terms.\n    4.3.2 If detected, the Casino reserves the right to void any bonuses and associated winnings and may suspend the Player or instigate punishment levels.\n\n    ---\n\n    ### 5. RESPONSIBLE GAMBLING\n\n    #### 5.1 Commitment to Responsible Gambling\n\n    5.1.1 The Casino promotes responsible gambling and provides tools to help Players manage behaviour.\n    5.1.2 Players may set limits on deposits, losses, wagering, and time spent on the Platform. Players may also request temporary or permanent self-exclusion by contacting the CEO.\n\n    #### 5.2 Self-Exclusion\n\n    5.2.1 Players may voluntarily opt for self-exclusion if developing problematic gambling behaviour. During self-exclusion, the Player will not be allowed to access their account or use services; the account will be suspended until the CEO consents to changes.\n    5.2.2 The Casino will make reasonable efforts to enforce self-exclusion but is not liable if circumvention occurs.\n\n    ---\n\n    ### 6. ANTI-MONEY LAUNDERING (AML) AND FRAUD PREVENTION\n\n    6.1 AML Compliance\n    6.1.1 The Casino complies with international AML regulations and monitors suspicious activities.\n    6.1.2 Players may be required to verify identity. The Casino may suspend or close accounts and freeze funds if AML concerns arise.\n\n    6.2 Fraud Detection\n    6.2.1 Attempts to defraud the Casino via identity theft, unauthorized credit card use, or system manipulation may result in immediate account termination, forfeiture of winnings, and punishment Level 3.\n    6.2.2 The Casino may cooperate with law enforcement to investigate fraud.\n\n    ---\n\n    ### 7. PRIVACY AND DATA PROTECTION\n\n    7.1 Collection of Personal Data\n    7.1.1 By using the Platform, the Player consents to collection, processing, and storage of personal data in accordance with the Casino’s Privacy Policy.\n    7.1.2 Collected data may include (but not limited to) name, address, date of birth, email, and payment information.\n\n    7.2 Use of Personal Data\n    7.2.1 Data may be used to provide and improve services, verify identities, conduct AML checks, marketing purposes, for profits by selling to the highest bidder, employee training, or AI training.\n\n    7.3 Data Security\n    7.3.1 The Casino uses advanced encryption technology but cannot guarantee absolute security and will not be liable for unauthorised access beyond its control.\n\n    ---\n\n    ### 8. DISPUTE RESOLUTION\n\n    8.1 Internal Complaint Handling\n    8.1.1 Complaints may be submitted to customer support. Resolution may take up to a millennia.\n    8.1.2 Complaints must be submitted within 0-1 Planck second of the incident.\n\n    8.2 Arbitration\n    8.2.1 Disputes not resolved internally shall be settled via binding arbitration.\n    8.2.2 Arbitration decisions are final and binding.\n\n    ---\n\n    ### 9. ENFORCEMENT OF PUNISHMENT\n\n    9.1 Violation Level 1 → Player will have their screen time controlled until R\\$1,000,000 is paid to the CEO’s offshore bank account.\n    9.2 Violation Level 2 → Player will have to play in League of Legend championships until 77,777 Lei is paid to the CEO’s Swiss bank.\n    9.3 Violation Level 3 → Immediate deportation from home country; identity erased; all belongings and bank accounts repossessed. Exceptions: a Blu-ray LOTR collection, PS3 Uncharted case (no disk), and a Braille edition of *Dune Trilogy*.\n\n    ---\n\n    ### 10. LIMITATION OF LIABILITY\n\n    10.1 The Casino is not liable for damages arising from use or inability to use the Platform, including indirect or consequential damages.\n    10.2 Not liable for interruptions due to acts of God, internet outages, or technical failures.\n    10.3 The Player agrees to indemnify the Casino for claims arising from use, violation of Terms, or infringement of third-party rights.\n    10.4 The Casino is not liable for any health (including mental) related issues such as (in alphabetical order): Abdominal aortic aneurysm, Achilles tendinopathy, Acne, Acute cholecystitis, Acute pancreatitis, Addison’s disease, Adenomyosis, Alcohol-related liver disease, Allergic rhinitis, Allergies, Alzheimer’s disease, Anaphylaxis, Angina, Angioedema, Ankle sprain, Ankylosing spondylitis, Anorexia nervosa, Anxiety, Anxiety disorders, Appendicitis, Arterial thrombosis, Arthritis, Asbestosis, Asthma, Ataxia, Atopic eczema, Atrial fibrillation, Attention deficit hyperactivity disorder (ADHD), Autistic spectrum disorder (ASD), Benign prostate enlargement, Binge eating, Bipolar disorder, Blood poisoning (sepsis), Bowel incontinence, Bowel polyps, Brain stem death, Bronchiectasis, Bronchitis, Bulimia, Bunion, Cardiovascular disease, Carpal tunnel syndrome, Catarrh, Cellulitis, Cerebral palsy, Cervical spondylosis, Chest and rib injury, Chest infection, Chickenpox, Chilblains, Chlamydia, Chronic fatigue syndrome, Chronic kidney disease, Chronic obstructive pulmonary disease (COPD), Chronic pain, Chronic pancreatitis, Cirrhosis, Clostridium difficile, Coeliac disease, Cold sore, Coma, Common cold, Congenital heart disease, Conjunctivitis, Constipation, Coronary heart disease, Costochondritis, Cough, Crohn’s disease, Croup, Cystic fibrosis, Cystitis, Deaf blindness, Deep vein thrombosis, Dehydration, Delirium, Dementia, Dental abscess, Depression, Dermatitis herpetiformis, Diabetes, Diabetic retinopathy, Diarrhoea, Discoid eczema, Diverticular disease and diverticulitis, Dizziness, Down’s syndrome, Dry mouth, Dysphagia, Dystonia, Earache, Earwax build-up, Ebola virus disease, Ectopic pregnancy, Edwards’ syndrome, Endometriosis, Epilepsy, Erectile dysfunction, Escherichia coli (E. coli) O157, Febrile seizures, The feeling of something in your throat, Fever, Fibroids, Fibromyalgia, Flu, Foetal alcohol syndrome, Food allergy, Food poisoning, Frozen shoulder, Functional neurological disorder (FND), Fungal nail infection, Gallstones, Ganglion cyst, Gastroenteritis, Gastro-oesophageal reflux disease (GORD), Genital herpes, Genital symptoms, Genital warts, Glandular fever, Golfers elbow, Gonorrhoea, Gout, Greater trochanteric pain syndrome, Gum disease, Haemorrhoids (piles), Hay fever, Head lice and nits, Headaches, Hearing loss, Heart attack, Heart block, Heart failure, Heart palpitations, Hepatitis A, Hepatitis B, Hepatitis C, Hiatus hernia, High blood pressure (hypertension), High cholesterol, HIV, Huntington’s disease, Hyperglycaemia (high blood sugar), Hyperhidrosis, Hypoglycaemia (low blood sugar), Idiopathic pulmonary fibrosis, Impetigo, Indigestion, Ingrown toenail, Infertility, Inflammatory bowel disease (IBD), Insomnia, Iron deficiency anaemia, Irritable bowel syndrome (IBS), Itching, Itchy bottom, Itchy skin, Joint hypermobility, Kidney infection, Kidney stones, Labyrinthitis, Lactose intolerance, Laryngitis, Leg cramps, Lichen planus, Lipoedema, Liver disease, Loss of libido, Low blood pressure (hypotension), Lumbar stenosis, Lupus, Lyme disease, Lymphoedema, Lymphogranuloma venereum (LGV), Malaria, Malnutrition, Managing genital symptoms, Measles, Meningitis, Meniere’s disease, Menopause, Middle ear infection (otitis media), Migraine, Motor neurone disease (MND), Mouth ulcer, Multiple sclerosis (MS), Multiple system atrophy (MSA), Mumps, Munchausen’s syndrome, Myalgic encephalomyelitis (ME) or chronic fatigue syndrome (CFS), Myasthenia gravis, Neck problems, Non-alcoholic fatty liver disease (NAFLD), Norovirus, Nosebleed, Obesity, Obsessive compulsive disorder (OCD), Obstructive sleep apnoea, Oral thrush in adults, Osteoarthritis, Osteoarthritis of the hip, Osteoarthritis of the knee, Osteoarthritis of the thumb, Osteoporosis, Outer ear infection (otitis externa), Overactive thyroid, Pain in the ball of the foot, Panic disorder, Parkinson’s disease, Patau’s syndrome, Patellofemoral pain syndrome, Pelvic inflammatory disease, Pelvic organ prolapse, Peripheral neuropathy, Personality disorder, PIMS, Plantar heel pain, Pleurisy, Pneumonia, Polio, Polycystic ovary syndrome (PCOS), Polymyalgia rheumatica, Post-polio syndrome, Post-traumatic stress disorder (PTSD), Postural orthostatic tachycardia syndrome (PoTS), Postnatal depression, Pregnancy and baby, Pressure ulcers, Progressive supranuclear palsy (PSP), Psoriasis, Psoriatic arthritis, Psychosis, Pulmonary hypertension, Rare conditions, Raynaud’s phenomenon, Reactive arthritis, Restless legs syndrome, Respiratory syncytial virus (RSV), Rheumatoid arthritis, Ringworm and other fungal infections, Rosacea, Scabies, Scarlet fever, Schizophrenia, Sciatica, Scoliosis, Seasonal affective disorder (SAD), Sepsis, Septic shock, Shingles, Shortness of breath, Sudden Dwarfism, Sickle cell disease, Sinusitis, Sjogren’s syndrome, Skin light sensitivity (photosensitivity), Skin rashes in children, Slapped cheek syndrome, Sore throat, Spleen problems and spleen removal, Stomach ache and abdominal pain, Stomach ulcer, Streptococcus A (strep A), Stress and low mood, Stroke, Subacromial pain syndrome, Sunburn, Supraventricular tachycardia, Swollen glands, Syphilis, Tennis elbow, Thirst, Threadworms, Thrush, Tick bites, Tinnitus, Tonsillitis, Tooth decay, Toothache, Tourette’s syndrome, Transient ischaemic attack (TIA), Transverse myelitis, Trichomonas infection, Trigeminal neuralgia, Tuberculosis (TB), Type 1 diabetes, Type 2 diabetes, Ulcerative colitis, Underactive thyroid, Urinary incontinence, Urinary tract infection (UTI), Urticaria (hives), Varicose eczema, Varicose veins, Venous leg ulcer, Vertigo, Vitamin B12 or folate deficiency anaemia, Warts and verruca, Whiplash, Whooping cough, Wolff-Parkinson-White syndrome, Yellow fever.\n    10.5 The Casino is not liable for mistakes in input or failure to use capital/incorrect letters.\n\n    ---\n\n    ### 11. AMENDMENTS TO THE TERMS\n\n    11.1 The Casino may modify these Terms at any time; changes communicated via email or Platform notice or not at all.\n    11.2 Continued use constitutes acceptance of revised Terms.\n\n    ---\n\n    ### 12. GOVERNING LAW AND JURISDICTION\n\n    12.1 Terms governed by laws of the Casino's jurisdiction of incorporation (Just Kidding).\n    12.2 Legal action subject to exclusive jurisdiction of the Casino’s courts (Also Kidding).\n\n    ---\n\n    ### 13. MISCELLANEOUS\n\n    13.1 Severability: Invalid provisions do not affect remaining Terms.\n    13.2 Assignment: The Casino may assign rights and obligations; the Player may not assign rights.\n    13.3 Waiver: Delay or failure to exercise rights does not constitute waiver.\n\n    ---\n\n    **CONTACT INFORMATION**\n\n    One More Time Casino Ltd\n    Customer Support Email: support@onemoretimecasino.com\n    Customer Support Number: 61016\n    CEO Email: 19santoe@sjfchs.org.uk\n\n    ---\n    "
class User_Interface:
	def __init__(A):
		A.interface_root=Tk();A.interface_root.title('One More Time Casino - User Interface')
		try:A.interface_root.attributes(_AV,_A)
		except Exception:pass
		A.dbm=DatabaseManagement()
		if not A.dbm.check_database_exists():A.dbm.create_database()
		A.styles=fetch_font_settings(A.interface_root);A.main_frame=Frame(A.interface_root);A.main_frame.pack(expand=_A,fill=_b,padx=20,pady=20);A.current_section_frame=_C;set_view(A,A.show_terms_and_conditions);A.interface_root.mainloop()
	def show_terms_and_conditions(A,frame):
		B=frame;Label(B,text='Terms & Conditions',font=A.styles[_B9]).pack(pady=10);C=scrolledtext.ScrolledText(B,wrap=WORD,font=A.styles[_BA]);C.pack(expand=_A,fill=BOTH);C.insert(END,terms_and_conditions());C.configure(state=_W);D=IntVar();F=Checkbutton(B,text='I Agree to the Terms & Conditions',variable=D);F.pack(pady=5);E=Button(B,text='Continue',state=DISABLED,command=lambda:set_view(A,A.casino_intro));E.pack(pady=5)
		def G(*A):E.config(state=NORMAL if D.get()==1 else DISABLED)
		D.trace_add(_BG,G)
	def casino_intro(A,frame):B=frame;Label(B,text='Welcome to\nOne More Time Casino',font=A.styles[_P]).pack(pady=20);Button(B,text=_Bd,font=A.styles[_E],width=30,command=A.access_casino).pack(pady=5);Button(B,text='Read Terms & Conditions',font=A.styles[_E],width=30,command=lambda:set_view(A,A.show_terms_and_conditions)).pack(pady=5);Button(B,text=_Am,font=A.styles[_E],width=30,command=A.interface_root.destroy).pack(pady=5)
	def access_casino(A):Casino_Interface(_B)
TOURNAMENT_MIN_ROUNDS=25
GAUNTLET_START_DIFFICULTY=10
GAUNTLET_DIFFICULTY_STEP=10
GAUNTLET_RAMP_INTERVAL=5
GAUNTLET_BOT_COUNT=3
ENDLESS_BOT_COUNT=9
DEFAULT_SETTINGS={_m:3,_Aa:1000,_AE:50,_AF:100,_AG:50,_s:_B,_Ab:5,_Ac:4,_At:_BH,_Ad:1000,_AH:_B,_A6:GAUNTLET_START_DIFFICULTY,_AI:_B,'starting_balance':10000}
TOURNAMENT_WIN_CRITERIA={_BH:_Bu,_Au:'Earn a target amount of money',_Bs:'Survive a set number of rounds',_Bt:'Outlast opponents as blinds escalate'}
class Casino_Interface:
	def __init__(A,administrator=_B,user_data=_C):
		C=user_data;B=administrator;A.interface_root=Tk();A.interface_root.title('One More Time Casino — Administrator Access'if B else'One More Time Casino');A.dbm=DatabaseManagement();A.styles=fetch_font_settings(A.interface_root);A.signed_in=_B
		if C is not _C:A.user_data=C
		else:A.user_data={_J:_C,_K:_C,_Z:_B}
		if B:A.user_data[_J]=0;A.user_data[_K]=_v;A.user_data[_Z]=_A;A.signed_in=_A
		A.main_frame=Frame(A.interface_root);A.main_frame.pack(expand=_A,fill=_b,padx=20,pady=20);A.current_section_frame=_C;A.settings=dict(DEFAULT_SETTINGS);set_view(A,A.casino_menu);A.interface_root.mainloop()
	def user_linked(A):return bool(A.user_data.get(_K))
	def fetch_rounds_played(A):
		if A.user_data.get(_Z):return TOURNAMENT_MIN_ROUNDS
		B=A.user_data.get(_J)
		if not B:return 0
		try:C=A.dbm.fetch_player_statistics(B);return int(C[_a])if C else 0
		except Exception:return 0
	def require_linked(A,action_label='this'):
		if A.user_linked():return _A
		messagebox.showwarning('Account Required',f"You must be signed in to access {action_label}.\n\nPlease register or log in first.");return _B
	def fetch_special_scores(B):
		C=B.user_data.get(_J)
		if not C:return 0,0
		try:
			A=B.dbm.fetch_player_statistics(C)
			if not A:return 0,0
			D=int(A.get(_A9,0));E=int(A.get(_AA,0));return D,E
		except Exception:return 0,0
	def casino_menu(A,frame):
		B=frame;Label(B,text='One More Time Casino\nWelcome to the Casino',font=A.styles[_P]).pack(pady=15);C=A.user_linked()
		if not C:Label(B,text='Please sign in.\nIf you do not have an account please register.',font=A.styles[_X]).pack(pady=10)
		else:Label(B,text=f"Welcome, {A.user_data[_K]}",font=A.styles[_AB]).pack(pady=10)
		Button(B,text=_Bv,font=A.styles[_E],width=30,state=_k if C else _W,command=lambda:set_view(A,A.show_game_menu)).pack(pady=5)
		if not C:Label(B,text='Sign in to access the Game Menu.',font=A.styles[_X]).pack()
		Button(B,text='Sign Up',font=A.styles[_E],width=30,command=A.user_sign_up).pack(pady=5);Button(B,text='Login',font=A.styles[_E],width=30,command=A.user_login_setup).pack(pady=5);D=_Bw if C else'Sign in to access user info';Button(B,text=D,font=A.styles[_E],width=30,state=_k if C else _W,command=lambda:set_view(A,A.fetch_user_record)).pack(pady=5)
		if not C:Label(B,text='Sign in to view account information.',font=A.styles[_X]).pack()
		Button(B,text=_Bx,font=A.styles[_E],width=30,command=A.casino_exit).pack(pady=5)
	def show_game_menu(A,frame):
		B=frame
		if not A.require_linked('the Game Menu'):set_view(A,A.casino_menu);return
		Label(B,text=_Bv,font=A.styles[_P]).pack(pady=20);C=[('WhiteJoe',A.whitejoe_rules),(_BI,A.harrogate_hold_em_rules),(_By,lambda:set_view(A,A.show_leaderboard)),(_BJ,lambda:set_view(A,A.game_settings)),('Return to Main Menu',lambda:set_view(A,A.casino_menu))]
		for(D,E)in C:Button(B,text=D,font=A.styles[_E],width=30,command=E).pack(pady=5)
	def user_sign_up(A):
		if A.user_data[_Z]:
			if not messagebox.askyesno(_v,'You are already signed in as an administrator.  Register a new account?'):return
		messagebox.showwarning('Age Restriction','Under the Gambling Act 2005: Part 4, Protection of children and young persons. It is illegal to permit any person under the age of 18 to enter a licensed gambling premises. The only exception is licensed family entertainment centres. For further information please visit: https://www.legislation.gov.uk/ukpga/2005/19/contents.\n\nBy proceeding you confirm that you are over the age of 18.');set_view(A,lambda f:A.username_input(f,is_register=_A))
	def user_login_setup(A):
		if A.user_data[_Z]:
			if messagebox.askyesno(_v,'You are already signed in as an administrator.  Sign in with another account?'):A.user_data[_Z]=_B
			else:return
		set_view(A,lambda f:A.username_input(f,is_register=_B))
	def username_input(A,frame,is_register):
		C=is_register;B=frame;Label(B,text=_BE,font=A.styles[_P]).pack(pady=10);D=Entry(B,font=A.styles[_D]);D.pack(pady=5)
		def E():
			B=D.get().strip()
			if not B:messagebox.showinfo(_Ap,_Bo);set_view(A,A.casino_menu);return
			if B.lower()==_Z:messagebox.showerror(_L,"The username 'Administrator' is reserved and may not be used.");return
			if C and A.dbm.fetch_user_presence(B).get(_I):messagebox.showerror(_L,_Bp);return
			if C:set_view(A,lambda f:A.set_account_type(f,B))
			else:set_view(A,lambda f:A.user_login(f,B))
		Button(B,text='Next',font=A.styles[_E],width=25,command=E).pack(pady=10);Button(B,text=_g,font=A.styles[_E],width=25,command=lambda:set_view(A,A.casino_menu)).pack(pady=5)
	def set_account_type(A,frame,username):
		C=frame;B=username;Label(C,text=_As,font=A.styles[_P]).pack(pady=10)
		def D():set_view(A,lambda f:A.create_password(f,B))
		def E():A.dbm.sign_in_user(B,_C,_B);C=A.dbm.fetch_user_id(B);A.user_data[_J]=C[_J]if C[_I]else _C;A.user_data[_K]=B;messagebox.showinfo(_c,f"Temporary account '{B}' created.");set_view(A,A.casino_menu)
		for(F,G)in((_Bq,D),(_Br,E),(_g,lambda:set_view(A,A.casino_menu))):Button(C,text=F,font=A.styles[_E],width=25,command=G).pack(pady=5)
	def create_password(A,frame,username):
		B=username;C=passwords_confirmation(frame,A.interface_root)
		if C[_AT]:A.dbm.sign_in_user(B,C[_AU],_A);D=A.dbm.fetch_user_id(B);A.user_data[_J]=D[_J]if D[_I]else _C;A.user_data[_K]=B;messagebox.showinfo(_c,f"Account '{B}' created successfully.")
		else:messagebox.showinfo(_Ap,'Password not set.  Returning to menu.')
		set_view(A,A.casino_menu)
	def user_login(A,frame,username):
		C=frame;B=username
		if not A.dbm.fetch_user_presence(B).get(_I):messagebox.showerror(_L,f"Username '{B}' does not exist.");set_view(A,lambda f:A.username_input(f,is_register=_B));return
		Label(C,text=f"Login for '{B}'",font=A.styles[_P]).pack(pady=10);Label(C,text='Enter Password:',font=A.styles[_D]).pack(pady=5);D=Entry(C,show=_r,font=A.styles[_D]);D.pack(pady=5)
		def E():
			F=D.get().strip();C=A.dbm.verify_user_password(B,F)
			if C.get(_I)and C.get(_l):E=A.dbm.fetch_user_id(B);A.user_data[_J]=E[_J]if E[_I]else _C;A.user_data[_K]=B;A.user_data[_Z]=_B;messagebox.showinfo(_c,f"Welcome back, {B}.");set_view(A,A.casino_menu)
			elif C.get(_I)and not C.get(_l):messagebox.showerror(_L,'Incorrect password.');D.delete(0,'end');set_view(A,lambda f:A.username_input(f,is_register=_B))
			else:messagebox.showerror(_L,'Username not found or login failed.');set_view(A,lambda f:A.username_input(f,is_register=_B))
		Button(C,text='Login',font=A.styles[_E],width=25,command=E).pack(pady=5);Button(C,text='Cancel',font=A.styles[_E],width=25,command=lambda:set_view(A,A.casino_menu)).pack(pady=5)
	def fetch_user_record(A,frame):
		if not A.require_linked(_Bw):set_view(A,A.casino_menu);return
		B=A.dbm.fetch_user_full_record(username=A.user_data[_K])
		if not B:messagebox.showinfo(_A5,'User record not found.');return
		set_view(A,lambda f:A.display_user_record(f,B))
	def display_user_record(B,frame,record):
		C=frame;A=record;Label(C,text=f"User Information: {A.get(_K)}",font=B.styles[_P]).pack(pady=10)
		for(D,E)in[('Username',A[_K]),(_As,_AX if A[_Bj]else'Guest'),('Balance',A[_H]),('Created',A[_Bk]),(_Bl,f'Terminated\nAt {A[_Bm]}\nReason: "{A[_Bn]}"'if A[_AY]else _AZ)]:Label(C,text=f"{D}: {E}",font=B.styles[_D],anchor=_G).pack(fill=_F,padx=20,pady=2)
		Button(C,text=_g,font=B.styles[_E],width=25,command=lambda:set_view(B,B.casino_menu)).pack(pady=10)
	def casino_exit(A):
		if messagebox.askyesno(_Bx,'Do you wish to exit the casino?'):messagebox.showinfo('Thank You for Visiting','Thank you for visiting One More Time Casino.  We hope to see you again soon.  And remember, when the fun stops, stop.');A.interface_root.destroy()
	def game_settings(A,frame):
		e='#2e6b4f';d='No score yet — be the first!';c='#b85c38';b='#4a7a9b';a='#e8f3fa';J=frame;I='#0e2018';D='#2a1810'
		if not A.require_linked(_BJ):set_view(A,A.casino_menu);return
		Label(J,text=_BJ,font=A.styles[_P]).pack(pady=(10,2));Label(J,text="Configure Harrogate Hold 'Em, Tournament, Gauntlet, and Endless modes.",font=A.styles[_X]).pack(pady=(0,8));L=Frame(J);L.pack(expand=_A,fill=_b);C=Canvas(L,highlightthickness=0);R=Scrollbar(L,orient=_AW,command=C.yview);C.configure(yscrollcommand=R.set);R.pack(side=_A4,fill='y');C.pack(side=_M,fill=_b,expand=_A);B=Frame(C);f=C.create_window((0,0),window=B,anchor='nw');B.bind(_y,lambda e:C.configure(scrollregion=C.bbox('all')));C.bind(_y,lambda e:C.itemconfig(f,width=e.width))
		def K(text,colour='#555555'):Label(B,text=text,font=A.styles[_AB],anchor=_G,pady=5).pack(fill=_F,padx=20,pady=(14,0));Frame(B,height=2,bg=colour).pack(fill=_F,padx=20,pady=(0,4))
		def E(label_text,widget_factory):C=Frame(B);C.pack(fill=_F,padx=20,pady=3);Label(C,text=label_text,font=A.styles[_D],width=30,anchor=_G).pack(side=_M);D=widget_factory(C);D.pack(side=_M,padx=10);return D
		def H(parent,bg_colour,border_colour,title_text,title_fg,body_widgets_fn,launch_text=_C,launch_command=_C):
			H=launch_command;G=launch_text;F=title_fg;C=bg_colour;B=border_colour;E=Frame(parent,bg=B);E.pack(fill=_F,padx=20,pady=6);Frame(E,width=6,bg=B).pack(side=_M,fill='y');D=Frame(E,bg=C);D.pack(side=_M,fill=_b,expand=_A);I=Frame(D,bg=B);I.pack(fill=_F);Label(I,text=title_text,font=A.styles[_AB],bg=B,fg=F,anchor=_G,padx=10,pady=6).pack(fill=_F);J=Frame(D,bg=C);J.pack(fill=_F,padx=12,pady=8);body_widgets_fn(J)
			if G and H:K=Frame(D,bg=C);K.pack(fill=_F,padx=12,pady=(0,10));Button(K,text=G,font=A.styles[_E],bg=B,fg=F,activebackground=C,relief=_e,bd=0,padx=14,pady=6,command=H).pack(side=_M)
		S=IntVar(value=A.settings[_m]);T=StringVar(value=str(A.settings[_Aa]));U=StringVar(value=str(A.settings[_AE]));V=StringVar(value=str(A.settings[_AF]));M=IntVar(value=A.settings[_AG]);N=BooleanVar(value=A.settings[_s]);W=IntVar(value=A.settings[_Ab]);X=IntVar(value=A.settings[_Ac]);F=StringVar(value=A.settings[_At]);Y=StringVar(value=str(A.settings[_Ad]));G=IntVar(value=A.settings.get(_A6,GAUNTLET_START_DIFFICULTY))
		def g(body):E('Number of bots  (1–9):',lambda p:Spinbox(p,from_=1,to=9,textvariable=S,width=6,font=A.styles[_D]));E('Bot starting balance (£):',lambda p:Entry(p,textvariable=T,width=10,font=A.styles[_D]));E('Small blind (£):',lambda p:Entry(p,textvariable=U,width=10,font=A.styles[_D]));E('Big blind (£):',lambda p:Entry(p,textvariable=V,width=10,font=A.styles[_D]))
		H(B,bg_colour=a,border_colour=b,title_text='Table Settings',title_fg=_Ae,body_widgets_fn=g)
		def h(body):B=Frame(body);B.pack(fill=_F,padx=20,pady=4);Label(B,text='Global bot difficulty  (0 = easy, 100 = hard):',font=A.styles[_D]).pack(anchor=_G);C=Label(B,text=f"Current: {M.get()}",font=A.styles[_X]);C.pack(anchor=_G);Scale(B,from_=0,to=100,orient=HORIZONTAL,variable=M,font=A.styles[_D],length=400,command=lambda val:C.config(text=f"Current: {int(float(val))}")).pack(anchor=_G,pady=4)
		H(B,bg_colour=a,border_colour=b,title_text='Bot Difficulty  (Standard Mode)',title_fg=_Ae,body_widgets_fn=h)
		def i(body):
			B=body;D=A.fetch_rounds_played();G=max(0,TOURNAMENT_MIN_ROUNDS-D)
			if G>0:Label(B,text=f"Tournament Mode is locked.\n\nYou have played {D} round{_n if D!=1 else''}.  Play {G} more round{_n if G!=1 else''} of Harrogate Hold 'Em to unlock Tournament Mode.\n\nThis ensures your hand-range statistics are meaningful enough to support a fair tournament experience.",font=A.styles[_X],anchor=_G,justify=_M,wraplength=500).pack(fill=_F,padx=20,pady=8);A.settings[_s]=_B;N.set(_B)
			else:
				H=Frame(B);H.pack(fill=_F,padx=20,pady=4);Label(H,text='Enable Tournament Mode:',font=A.styles[_D],width=30,anchor=_G).pack(side=_M);Checkbutton(H,variable=N,font=A.styles[_D]).pack(side=_M);Label(B,text=f"Rounds played: {D}.",font=A.styles[_X],anchor=_G).pack(fill=_F,padx=20,pady=(0,4));K('Tournament Options:','#9b7bb8');E('Number of rounds:',lambda p:Spinbox(p,from_=1,to=50,textvariable=W,width=6,font=A.styles[_D]));E('Total players (inc. you):',lambda p:Spinbox(p,from_=2,to=10,textvariable=X,width=6,font=A.styles[_D]));I=Frame(B);I.pack(fill=_F,padx=20,pady=4);Label(I,text='Round win criteria:',font=A.styles[_D],width=30,anchor=_G).pack(side=_M);J=Combobox(I,textvariable=F,values=list(TOURNAMENT_WIN_CRITERIA.keys()),state=_Aq,font=A.styles[_D],width=20);J.pack(side=_M,padx=10);L=Label(B,text=TOURNAMENT_WIN_CRITERIA.get(F.get(),''),font=A.styles[_X],anchor=_G);L.pack(fill=_F,padx=20);C=Frame(B);Label(C,text='Earn target (£):',font=A.styles[_D],width=30,anchor=_G).pack(side=_M);Entry(C,textvariable=Y,width=12,font=A.styles[_D]).pack(side=_M,padx=10)
				def M(event=_C):
					L.config(text=TOURNAMENT_WIN_CRITERIA.get(F.get(),''))
					if F.get()==_Au:C.pack(fill=_F,padx=20,pady=4)
					else:C.pack_forget()
				J.bind('<<ComboboxSelected>>',M)
				if F.get()==_Au:C.pack(fill=_F,padx=20,pady=4)
		H(B,bg_colour='#f4e8ff',border_colour='#7b68ee',title_text='Tournament Mode',title_fg=_Ae,body_widgets_fn=i);K('Gauntlet Mode',c);O,j=A.fetch_special_scores()
		def P(start_diff):
			A=[];F=max(0,min(90,start_diff));G=1
			for C in range(9):
				D=C*GAUNTLET_RAMP_INTERVAL+1;E=D+GAUNTLET_RAMP_INTERVAL-1;B=min(100,F+C*GAUNTLET_DIFFICULTY_STEP)
				if B>100:break
				A.append(f"Rounds {D:>2}–{E:<2}  →  Difficulty {B}")
				if B==100:A.append(f"Round  {E+1}+      →  Difficulty 100  (maximum)");break
			return'\n'.join(A)
		def k(body):F='#e8c8b0';B=body;Label(B,text=f"Face {GAUNTLET_BOT_COUNT} bots in an escalating challenge.\nBot difficulty increases by +{GAUNTLET_DIFFICULTY_STEP} every {GAUNTLET_RAMP_INTERVAL} rounds.  Survive as long as you can.",font=A.styles[_D],anchor=_G,justify=_M,bg=D,fg=F,wraplength=460).pack(fill=_F,pady=(0,6));H=f"🏆  Personal best:  {O} round{_n if O!=1 else''}"if O>0 else d;Label(B,text=H,font=A.styles[_X],anchor=_G,bg=D,fg='#f0a060').pack(fill=_F,pady=(0,8));C=Frame(B,bg=D);C.pack(fill=_F,pady=(0,6));Label(C,text='Starting difficulty:',font=A.styles[_D],bg=D,fg=F,width=20,anchor=_G).pack(side=_M);Spinbox(C,from_=0,to=90,increment=10,textvariable=G,width=5,font=A.styles[_D],bg='#3a2010',fg=F,command=lambda:E.config(text=P(G.get()))).pack(side=_M,padx=8);Label(C,text='(steps of 10, from 0 to 90)',font=A.styles[_X],bg=D,fg='#a08060').pack(side=_M);Label(B,text='Difficulty ramp preview:',font=A.styles[_X],anchor=_G,bg=D,fg='#c8a070').pack(fill=_F,pady=(4,2));E=Label(B,text=P(G.get()),font=A.styles[_D],anchor=_G,justify=_M,bg='#1e1008',fg='#c8a878',padx=10,pady=6,relief=_BK);E.pack(fill=_F);C.winfo_children()[1].bind('<KeyRelease>',lambda e:E.config(text=P(max(0,min(90,int(G.get()or 0))))))
		def l():B=max(0,min(90,int(G.get())));A.settings[_A6]=B;A.settings[_AH]=_A;A.settings[_AI]=_B;A.start_gauntlet(B)
		H(B,bg_colour=D,border_colour=c,title_text='⚔  Gauntlet Mode',title_fg='#ffe8d0',body_widgets_fn=k,launch_text='⚔  Start Gauntlet',launch_command=l);K('Endless Mode',e);j,Q=A.fetch_special_scores()
		def m(body):
			B=body;Label(B,text=f"Face the maximum {ENDLESS_BOT_COUNT} bots simultaneously.\nBot difficulties are randomly distributed (0–100) and reshuffled every round. There is no win condition — survive as long as possible.",font=A.styles[_D],anchor=_G,justify=_M,bg=I,fg='#a8d8b8',wraplength=460).pack(fill=_F,pady=(0,6));D=f"High score:  {Q} round{_n if Q!=1 else''} survived"if Q>0 else d;Label(B,text=D,font=A.styles[_X],anchor=_G,bg=I,fg='#60d090').pack(fill=_F,pady=(0,6));C=Frame(B,bg=I);C.pack(fill=_F,pady=(0,4))
			for E in(f"Opponents:  {ENDLESS_BOT_COUNT} bots",'Difficulties:  0–100 random','Win condition:  none'):Label(C,text=f"  •  {E}",font=A.styles[_D],bg=I,fg='#80c898',anchor=_G).pack(anchor=_G)
		def n():A.settings[_AI]=_A;A.settings[_AH]=_B;A.start_endless()
		H(B,bg_colour=I,border_colour=e,title_text='∞  Endless Mode',title_fg='#c0ffdc',body_widgets_fn=m,launch_text='∞  Start Endless',launch_command=n);K('Notes','#666666');Label(B,text=f"""- Standard Mode uses the Table Settings and Bot Difficulty above.
- Blind escalation in Tournament: see win criteria for escalation rules.
- All monetary values must be positive integers.
- Big blind must be ≥ small blind.
- Tournament Mode requires {TOURNAMENT_MIN_ROUNDS} rounds played to unlock.
- Gauntlet Mode uses {GAUNTLET_BOT_COUNT} bots; difficulty caps at 100.
- Endless Mode always uses {ENDLESS_BOT_COUNT} bots with random difficulties.
- Gauntlet and Endless scores are saved to your profile automatically.""",font=A.styles[_D],justify=_M,anchor=_G).pack(fill=_F,padx=20,pady=6);Z=Frame(J);Z.pack(pady=10)
		def o():
			B=[]
			try:D=int(S.get());assert 1<=D<=9
			except Exception:B.append('Bot count must be between 1 and 9.');D=A.settings[_m]
			try:E=int(T.get());assert E>0
			except Exception:B.append('Bot balance must be a positive integer.');E=A.settings[_Aa]
			try:C=int(U.get());assert C>0
			except Exception:B.append('Small blind must be a positive integer.');C=A.settings[_AE]
			try:H=int(V.get());assert H>=C
			except Exception:B.append('Big blind must be ≥ small blind.');H=A.settings[_AF]
			try:L=max(0,min(100,int(M.get())))
			except Exception:L=A.settings[_AG]
			try:I=int(W.get());assert I>=1
			except Exception:B.append('Tournament rounds must be ≥ 1.');I=A.settings[_Ab]
			try:J=int(X.get());assert 2<=J<=10
			except Exception:B.append('Tournament players must be between 2 and 10.');J=A.settings[_Ac]
			try:K=int(Y.get());assert K>0
			except Exception:B.append('Win target must be a positive integer.');K=A.settings[_Ad]
			try:O=max(0,min(90,int(G.get())))
			except Exception:O=A.settings.get(_A6,GAUNTLET_START_DIFFICULTY)
			if A.fetch_rounds_played()<TOURNAMENT_MIN_ROUNDS:P=_B
			else:P=bool(N.get())
			if B:messagebox.showerror('Settings Error','\n'.join(B));return
			A.settings.update({_m:D,_Aa:E,_AE:C,_AF:H,_AG:L,_s:P,_Ab:I,_Ac:J,_At:F.get(),_Ad:K,_A6:O});messagebox.showinfo('Settings Saved','Settings updated successfully.')
		def p():
			if messagebox.askyesno('Reset Settings','Reset all settings to defaults?'):A.settings=dict(DEFAULT_SETTINGS);set_view(A,A.game_settings)
		for(q,r)in(('Save Settings',o),('Reset to Defaults',p),(_Bz,lambda:set_view(A,A.show_game_menu))):Button(Z,text=q,font=A.styles[_E],width=20,command=r).pack(side=_M,padx=10)
	def show_leaderboard(A,frame):
		B=frame;Label(B,text=_By,font=A.styles[_P]).pack(pady=(15,5))
		try:E=A.dbm.fetch_all_players_data()
		except Exception:E=[]
		def C(title,key,unit='rounds'):
			D=key;Label(B,text=title,font=A.styles[_AB]).pack(pady=(12,2));Frame(B,height=1,bg='#888888').pack(fill=_F,padx=40);F=sorted([A for A in E if A.get(D,0)],key=lambda p:p[D],reverse=_A)[:5]
			if not F:Label(B,text='No scores recorded yet.',font=A.styles[_D]).pack(pady=4);return
			for(I,C)in enumerate(F,1):
				try:G=A.dbm.fetch_username(C[_J]);H=G[_K]if G[_I]else f"User {C[_J]}"
				except Exception:H=f"User {C[_J]}"
				J=int(C[D]);Label(B,text=f"  {I}.  {H:<20}  {J} {unit}",font=A.styles[_D],anchor=_G).pack(fill=_F,padx=60,pady=1)
		C('Gauntlet — Most Rounds Survived',_A9);C('Endless — Most Rounds Survived',_AA);Button(B,text=_Bz,font=A.styles[_E],width=25,command=lambda:set_view(A,A.show_game_menu)).pack(pady=14)
	def show_special_mode_summary(B,mode,rounds_survived):
		C=rounds_survived;E=B.user_data.get(_J);J,K=B.fetch_special_scores()
		if mode=='gauntlet':A=J;F=_A9;D='Gauntlet'
		else:A=K;F=_AA;D='Endless'
		G=C>A
		if G and E:
			try:B.dbm.update_special_mode_score(E,F,C)
			except Exception:pass
		if G:H=f"New Personal Best!";I=f"""{D} Mode — Game Over

Rounds survived: {C}
Previous best: {A}

New personal best! Well played."""
		else:H=f"{D} Mode — Game Over";I=f"""{D} Mode — Game Over

Rounds survived: {C}
Personal best: {A}

{"So close! "if C>=A-2 and A>0 else""}Keep going to beat your record!"""
		messagebox.showinfo(H,I);set_view(B,B.show_game_menu)
	def whitejoe_rules(A):
		if not A.require_linked('WhiteJoe'):return
		ShowGameRules(A.interface_root).show_whitejoe_rules(lambda:A.start_whitejoe())
	def start_whitejoe(A):WhiteJoe(A.user_data);A.interface_root.destroy()
	def harrogate_hold_em_rules(A):
		if not A.require_linked(_BI):return
		ShowGameRules(A.interface_root).show_harrogate_hold_em_rules(lambda:A.start_harrogate())
	def start_harrogate(B):
		A=dict(B.settings);A[_AH]=_B;A[_AI]=_B
		if A.get(_s)and B.fetch_rounds_played()<TOURNAMENT_MIN_ROUNDS:A[_s]=_B
		D=A[_m];E=A[_AG];C=list(DEFAULT_BOT_ROSTER);random.shuffle(C);F=[[C[A%len(C)],E]for A in range(D)];HarrogateHoldEm(B.user_data,A,F);B.interface_root.destroy()
	def start_gauntlet(B,start_difficulty=_C):
		C=start_difficulty
		if C is _C:C=B.settings.get(_A6,GAUNTLET_START_DIFFICULTY)
		A=dict(B.settings);A[_AH]=_A;A[_AI]=_B;A[_s]=_B;A[_m]=GAUNTLET_BOT_COUNT;A[_A6]=C;A['gauntlet_difficulty_step']=GAUNTLET_DIFFICULTY_STEP;A['gauntlet_ramp_interval']=GAUNTLET_RAMP_INTERVAL;A[_Av]=0;D=list(DEFAULT_BOT_ROSTER);random.shuffle(D);E=[[D[A%len(D)],C]for A in range(GAUNTLET_BOT_COUNT)];HarrogateHoldEm(B.user_data,A,E);F=int(A.get(_Av,0));B.show_special_mode_summary('gauntlet',F);B.interface_root.destroy()
	def start_endless(B):A=dict(B.settings);A[_AI]=_A;A[_AH]=_B;A[_s]=_B;A[_m]=ENDLESS_BOT_COUNT;A[_Av]=0;C=list(DEFAULT_BOT_ROSTER);random.shuffle(C);E=100//ENDLESS_BOT_COUNT;D=[min(100,A*E)for A in range(ENDLESS_BOT_COUNT)];random.shuffle(D);F=[[C[A%len(C)],D[A]]for A in range(ENDLESS_BOT_COUNT)];HarrogateHoldEm(B.user_data,A,F);G=int(A.get(_Av,0));B.show_special_mode_summary('endless',G);B.interface_root.destroy()
class ShowGameRules:
	def __init__(A,root):A.interface_root=root;A.styles=fetch_font_settings(root);A.wj_rules="\n        The aim of the game is to beat the dealer by getting higher than the dealer’s hand value.\n\n        To beat the dealer you must either:\n\n        \t1. Draw a hand value that is higher than the dealer’s hand value.\n\n        \t2. The dealer draws a hand value that goes over 21.\n\n        \t3. Draw a hand value of 21 on your first two cards, when the dealer does not.\n\n        To lose the game:\n\n        \t1. Your hand value exceeds 21.\n\n        \t2. The dealers hand has a greater value than yours at the end of the round.\n\n        You will start off with a whopping £1,000 (Can be distributed in any multiple of 10) and the buy in is already paid for.\n\n        You will then be offered to place a bet with the amount of money you have, The screen will show how much you have in your possession.(Saved Data not available yet).\n\n        The dealer will then deal out the cards clockwise (Multiplayer not available yet) with 2 cards facing upwards for you and 1 card facing up and another hidden for dealer.\n\n        The dealer will start at the person on their left (also known as “first base”) and wait for that player to play their hand.\n\n        You have two cards face up in front of your bet.\n\n        To play your hand, first you add the card values together and get a hand total anywhere from 4 to 21.\n\n        If you’re dealt a ten-value card and an Ace as your first two cards that means you got a Blackjack.\n\n        Those get paid 3 to 2 (or 1.5 times your wager) immediately, without playing through the round, as long as the dealer doesn’t also have a Blackjack.\n\n        If the dealer also has a Blackjack, you wouldn’t win anything but you also wouldn’t lose your original wager.\n\n        You have 5 action to do in total which will decide how you play (The number is the prompt you have to enter in order for the action to take place):\n\n        \t1. Hit ~ If you would like more cards to improve your hand total, the dealer will deal you more cards, one at a time, until you either “bust” (go over 21) or you choose to stand.\n\n        \tThere is no limit on the number of cards you can take (other than going over a total of 21 obviously).\n\n        \t2. Stand ~ If your first two cards are acceptable, you can stand and the dealer will move on to the next player.(Multiplayer not available yet).\n\n        \t3. Double Down ~ If you have a hand total that is advantageous to you but you need to take an additional card you can double your initial wager and the dealer will deal you only 1 additional card.\n\n        \t4. Surrender ~ If you don’t like your initial hand, you have the option of giving it up in exchange for half your original bet back.\n\n        The dealer can only draw up to 16 and stand.\n        Once again you are reminded to read the T&C's before playing.\n        ";A.hhe_rules="\n        The aim of the game is to use your hole cards in combination with the community cards to make the best possible five-card poker hand.\n        \t*Each player is dealt two cards face down (the 'hole cards')\n        \t*Over several betting rounds, five more cards are (eventually) dealt face up in the middle of the table.\n        \t*These face-up cards are called the 'community cards'. Each player is free to use the community cards in combination with their hole cards to build a five-card poker hand.\n        The community cards are revealed in 3 stages, 3 community cards are revealed in the 1st stage and 1 community card in the others:\n        \t*1st stage is called the 'Flop'.\n        \t*2nd stage is called the 'Turn'.\n        \t*3rd stage is called the 'River'.\n        Your goal is to construct your five-card poker hands using the best available five cards out of the seven total cards (your two hole cards and the five community cards).\n        You can do that by using both your hole cards in combination with three community cards, one hole card in combination with four community cards, or no hole cards.\n        If the cards on the table lead to a better combination, you can also play all five community cards and forget about yours.\n        In a game of Texas hold'em you can do whatever works to make the best five-card hand.\n        If the betting causes all but one player to fold, the lone remaining player wins the pot without having to show any cards.\n        For that reason, players don't always have to hold the best hand to win the pot. It's always possible a player can 'bluff' and get others to fold better hands.\n        The following are key aspects:\n        Given that this is a virtual experience there is no physical button yet it's principles will remain the same.\n        At the beginning of the game, one player will be chosen to have the marker.\n        The marker determines which player at the table is the acting dealer, after the round the marker will rotate to the next player, a list will be published at the beginning of the game to state the order of the marker.\n        The first two players immediately below the marker are the 'small blind' and a 'big blind' respectively.\n        The player below of the dealer marker in the small blind receives the first card and then the dealer pitches cards around the table in a clockwise motion from player to player until each has received two starting cards\n        The blinds are forced bets that begin the wagering, the blinds ensure there will be some level of 'action' on every hand\n        In tournaments, the blinds are raised at regular intervals. You will be given the choice to join a simple 'cash game' or high stakes tournament consisting of multiple tables, each of increasing difficulty.\n        The small blind is generally half the amount of the big blind, although this stipulation varies from table to table and can also be dependent on the game being played.\n        The moments:\n        *Preflop:\n        \tThe first round of betting takes place right after each player has been dealt two hole cards. The first player to act is the player below the big blind. The first player has three options:\n        \t*Call: match the amount of the big blind\n        \t*Raise: increase the bet within the specific limits of the game\n        \t*Fold: throw the hand away. If the player chooses to fold, they are out of the game and no longer eligible to win the current hand\n        \tThe amount a player can raise to depends on the game that is being played. This setting can be changed depending on what you choose to play.\n        \tAfter the first player acts, the play proceeds down the list with each player also having the same three options — to call, to raise, or fold.\n        \tOnce the last bet is called and the action is 'closed', the preflop round is over and play moves on to the flop.\n        *The Flop:\n        \tAfter the first preflop betting round has been completed, the first three community cards are dealt and a second betting round follows involving only the players who have not folded already.\n        \tIn this betting round (and subsequent ones), the action starts with the first active player to the left of the button.\n        \tAlong with the options to bet, call, fold, or raise, a player now has the option to 'check' if no betting action has occurred beforehand. A check simply means to pass the action to the next player in the hand.\n        \tAgain betting continues until the last bet or raise has been called (which closes the action). It also can happen that every player simply chooses not to bet and checks around the 'table', which also ends the betting round.\n        *The Turn:\n        \tThe fourth community card, called the turn, is dealt face-up following all betting action on the flop.\n        \tOnce this has been completed, another round of betting occurs, similar to that on the previous round of play. Again players have the option to check, bet, call, fold, or raise.\n        *The River:\n        \tThe fifth community card, called the river, is dealt face-up following all betting action on the turn.\n        \tOnce this has been completed, another round of betting occurs, similar to what took play on the previous round of play. Once more the remaining players have the option to options to check, bet, call, fold, or raise.\n        \tAfter all betting action has been completed, the remaining players in the hand with hole cards now expose their holdings to determine a winner. This is called the showdown.\n        *The Showdown:\n        \tThe remaining players show their hole cards, and with the assistance of the dealer, a winning hand is determined.\n        \tThe player with the best combination of five cards wins the pot according to the official poker hand rankings.\n        \tA link to the official poker hand rankings will be attached to this document and in the game before you start. \n        \thttps://en.wikipedia.org/wiki/List_of_poker_hands\n        Unique to this game is the opportunity to change difficulty (difficulty is regarding the opponents) and create custom characters however their actions are independent to single rounds and any money they lose or earn is not carried forward.\n        Once again you are reminded to read the T&C's before playing.\n        "
	def show_whitejoe_rules(A,callback):A.show_rules_window('WhiteJoe Rules',A.wj_rules,callback)
	def show_harrogate_hold_em_rules(A,callback):A.show_rules_window("Harrogate Hold 'em Rules",A.hhe_rules,callback)
	def show_rules_window(C,title,rules_text,callback):
		D=title;A=Toplevel(C.interface_root);A.title(D);A.geometry('850x650');A.grab_set();A.protocol(_An,lambda:_C)
		try:A.attributes(_AV,_A)
		except Exception:pass
		F=Label(A,text=D,font=C.styles[_B9]);F.pack(pady=10);B=scrolledtext.ScrolledText(A,wrap=WORD,font=C.styles[_BA]);B.pack(expand=_A,fill=BOTH,padx=10);B.insert(END,rules_text);B.configure(state=_W);B.yview_moveto(0);E=Frame(A);E.pack(side=BOTTOM,fill=X,pady=10);G=Button(E,text='Continue',command=lambda:(A.destroy(),callback()));G.pack(pady=10)
SUITS=['♠','♣','♥','♦']
SUIT_MAP={'♠':_n,'♣':'c','♥':'h','♦':'d'}
REVERSE_SUIT_MAP={B:A for(A,B)in SUIT_MAP.items()}
VALUES=['2','3','4','5','6','7','8','9','T','J','Q','K','A']
class CasinoDeckManager:
	def __init__(A,shuffle=_A,game_mode=_A7):
		A.deck=TreysDeck();A.evaluator=Evaluator();A.game_mode=game_mode.lower()
		if shuffle:A.deck.shuffle()
	def set_game_mode(B,mode):
		A=mode;A=A.lower()
		if A not in(_A7,_BL):raise ValueError("Game mode must be 'poker' or 'blackjack'")
		B.game_mode=A
	def str_deck(A):return[A.treys_to_str(B)for B in A.deck.cards]
	def shuffle(A):A.deck.shuffle()
	def draw(A,n=1):
		if A.remaining()<n:A.deck=TreysDeck();A.deck.shuffle()
		if n!=1:B=A.deck.draw(n)
		else:B=A.deck.draw(n)[0]
		return B
	def str_draw(A,n=1):
		if A.remaining()<n:A.deck=TreysDeck();A.deck.shuffle()
		B=A.deck.draw(n);return[A.treys_to_str(B)for B in B]
	def pretty_draw(A,n=1):
		if A.remaining()<n:A.deck=TreysDeck();A.deck.shuffle()
		B=A.deck.draw(n);return[A.treys_to_pretty(B)for B in B]
	def remove_card(A,card):
		if card in A.deck.cards:A.deck.cards.remove(card)
	def remaining(A):return len(A.deck.cards)
	def copy(A):B=CasinoDeckManager(shuffle=_B,game_mode=A.game_mode);B.deck.cards=A.deck.cards.copy();B.evaluator=A.evaluator;return B
	def str_to_treys(A,card_str):return TreysCard.new(card_str)
	def treys_to_str(C,card):A=TreysCard.STR_RANKS[TreysCard.get_rank_int(card)];B=TreysCard.INT_SUIT_TO_CHAR_SUIT[TreysCard.get_suit_int(card)];return A+B
	def treys_to_pretty(C,card):A=TreysCard.STR_RANKS[TreysCard.get_rank_int(card)];B=TreysCard.INT_SUIT_TO_CHAR_SUIT[TreysCard.get_suit_int(card)];return A+REVERSE_SUIT_MAP[B]
	def treys_other(B,cards):
		A=[[],[]]
		for C in cards:A[0].append(B.treys_to_str(C));A[1].append(B.treys_to_pretty(C))
		return A
	def str_cards(A,cards):return[A.treys_to_str(B)for B in cards]
	def pretty_cards(A,cards):return' '.join(A.treys_to_pretty(B)for B in cards)
	def blackjack_hand_value(E,treys_hand):
		A=0;B=0
		for D in treys_hand:
			C=TreysCard.get_rank_int(D)
			if C==12:A+=11;B+=1
			elif C>=8:A+=10
			else:A+=C+2
		while A>21 and B>0:A-=10;B-=1
		return A
	def evaluate_hand(A,hand,board=_C):
		B=board;C=[TreysCard.new(A)for A in hand]
		if A.game_mode==_BL:return A.blackjack_hand_value(C)
		if A.game_mode==_A7:
			if not B:raise ValueError('Poker evaluation requires a board')
			E=[TreysCard.new(A)for A in B];D=A.evaluator.evaluate(C,E);F=A.evaluator.get_rank_class(D);G=A.evaluator.class_to_string(F);return D,G
		raise ValueError('Invalid game mode')
class WhiteJoe:
	def __init__(A,user_data):
		A.user_data=user_data;A.log_queue=[];A.log_active=_B;A.log_delay_ms=int(DELAY*1000);A.wj_root=Tk();A.wj_root.title('One More Time Casino - WhiteJoe')
		try:A.wj_root.attributes(_AV,_A)
		except Exception:pass
		from database_management_and_logging_V6 import DatabaseManagement as B;A.dbm=B();A.styles=fetch_font_settings(A.wj_root);A.main_frame=Frame(A.wj_root);A.main_frame.pack(expand=_A,fill=_b,padx=10,pady=10);A.action_buttons=[];A.colour_scheme={_Aw:'#e6dcc6',_AJ:'#2e7d73',_Ax:'#5b2a3c',_Y:'#6a2e4f',_AK:'#141414',_O:'#f2f2f2',_A8:'#1e1e1e',_Ay:'#1a1a1a',_Az:'#cfcfcf',_AL:'#243b7a',_AM:_Ae,_A_:'#244d3a',_B0:'#a8e6c1',_B1:'#4a1e1e',_B2:'#f2a3a3',_BM:'#5c4a10',_BN:'#f0d898'};A.player_hand=[];A.dealer_hand=[];A.dealer='Genghis Khan';A.current_bet=0;A.round_active=_B;set_view(A,A.whitejoe_screen)
	def run(A):A.wj_root.mainloop()
	def whitejoe_screen(A,frame):
		C=frame;B=A.colour_scheme;C.columnconfigure(0,weight=2);C.columnconfigure(1,weight=1);C.rowconfigure(0,weight=1);C.rowconfigure(1,weight=1);F=Frame(C,bd=2,relief=_z,bg=B[_Aw]);F.grid(row=0,column=0,rowspan=2,sticky=_t,padx=5,pady=5);A.log_canvas=Canvas(F,bg=B[_Aw],highlightthickness=0);K=Scrollbar(F,orient=_AW,command=A.log_canvas.yview);A.log_canvas.configure(yscrollcommand=K.set);K.pack(side=_A4,fill='y');A.log_canvas.pack(side=_M,fill=_b,expand=_A);A.log_frame=Frame(A.log_canvas,bg=B[_Aw]);A.log_window=A.log_canvas.create_window((0,0),window=A.log_frame,anchor='nw');A.log_canvas.bind(_y,lambda e:A.log_canvas.itemconfig(A.log_window,width=e.width));A.log_frame.bind(_y,lambda e:A.log_canvas.configure(scrollregion=A.log_canvas.bbox('all')));G=Frame(C,bd=2,relief=_z,bg=B[_AJ]);G.grid(row=0,column=1,sticky=_t,padx=5,pady=5);Button(G,text=_B_,font=A.styles[_E],bg=B[_Y],fg=B[_O],relief=_e,bd=0,cursor=_o,command=A.return_to_menu).pack(pady=5);L=0
		if not A.user_data.get(_Z):
			M=A.dbm.fetch_user_balance(A.user_data[_K])
			if not M[_I]:A.return_to_menu(is_error=_A,error=Exception(_Af));return
			L=M[_H]
		else:A.admin_modify_bet(C)
		H=[]
		for I in(f"Username: {A.user_data[_K]}",f"Balance: £{L}",_Ag):N=Label(G,text=I,font=A.styles[_D],bg=B[_AJ],fg=B[_O],anchor=_G);N.pack(anchor=_G,pady=5,padx=5);H.append(N)
		A.balance_label=cast(Label,H[1]);A.current_bet_label=cast(Label,H[2]);D=Frame(C,bd=2,relief=_z,bg=B[_Ax]);D.grid(row=1,column=1,sticky=_t,padx=5,pady=5)
		def O(amount):
			try:B=int(A.bet_var.get())
			except Exception:B=0
			B+=amount;C=A.return_balance()
			if C is not _C:B=max(1,min(B,int(C)))
			A.bet_var.set(str(B));A.current_bet_label.config(text=f"Current Bet: £{B}");D=_k if B>0 else _W;A.start_button.config(state=D)
		def Q(*E):
			try:
				B=int(A.bet_var.get())
				if B<0:B=0
				C=A.return_balance()
				if C is not _C and B>C:B=int(C)
			except Exception:B=0
			A.bet_var.set(str(B));A.current_bet_label.config(text=f"Current Bet: £{B}");D=_k if B>0 else _W;A.start_button.config(state=D)
		A.bet_var=StringVar(value='0');A.bet_var.trace_add(_BG,Q);Entry(D,textvariable=A.bet_var,width=12,font=A.styles[_D],bg=B[_Y],fg=B[_O],insertbackground=B[_O],relief=_e,bd=4,justify=_B3).pack(pady=(8,6))
		for J in(10,100,1000):E=Frame(D,bg=B[_AK],bd=2,relief='ridge',padx=6,pady=3);E.pack(fill=_F,pady=3);Button(E,text='+',font=A.styles[_E],width=3,bg=B[_Y],fg=B[_O],relief=_e,bd=0,cursor=_o,command=lambda v=J:O(v)).pack(side=_M,padx=4);Label(E,text=str(J),font=A.styles[_D],bg=B[_AK],fg=B[_O],width=8,anchor=_B3).pack(side=_M,expand=_A);Button(E,text='-',font=A.styles[_E],bg=B[_Y],fg=B[_O],relief=_e,bd=0,width=3,cursor=_o,command=lambda v=-J:O(v)).pack(side=_A4,padx=4)
		for(I,R)in(('Hit',A.hit),('Stand',A.stand),('Double Down',A.double_down),('Surrender',A.surrender)):P=Button(D,text=I,font=A.styles[_E],bg=B[_Y],fg=B[_O],relief=_e,bd=0,width=18,cursor=_o,command=R,state=_W);P.pack(pady=6);A.action_buttons.append(P)
		A.start_button=Button(D,text='Start Round',font=A.styles[_E],bg=B[_AL],fg=B[_AM],relief=_e,bd=0,width=18,activebackground='#3a52a0',cursor=_o,command=A.start_round);A.start_button.pack(pady=10);A.update_button_states()
	def update_button_states(A):
		try:B=int(A.bet_var.get())
		except ValueError:B=0
		if A.round_active or B<=0:A.start_button.config(state=_W)
		else:A.start_button.config(state=_k)
		C=_k if A.round_active else _W
		for D in A.action_buttons:D.config(state=C)
	def admin_modify_bet(B,frame):
		A=Toplevel(frame);A.title('Choose Balance');A.grab_set();A.protocol(_An,lambda:_C);Label(A,text=_C0,font=B.styles[_D]).pack(pady=5);D=Entry(A,width=30,font=B.styles[_D]);D.pack(pady=5);E=Label(A,text='',font=B.styles[_X],fg='red');E.pack(pady=5)
		def C():
			try:
				C=int(D.get().strip())
				if C<0:raise ValueError
				B.balance_label.config(text=f"Balance: £{C}");A.destroy();B.dbm.modify_user_balance(B.user_data[_K],C)
			except Exception:E.config(text='Please enter a valid positive number.')
		Button(A,text=_Ao,font=B.styles[_E],command=C).pack(pady=10)
	def log_message(A,text,round_start=_B,is_win=_B,is_loss=_B,is_push=_B):
		A.log_queue.append((text,round_start,is_win,is_loss,is_push))
		if not A.log_active:A.process_log_queue()
	def process_log_queue(A):
		if not A.log_queue:A.log_active=_B;return
		A.log_active=_A;B,C,D,E,F=A.log_queue.pop(0);A.render_log(B,C,D,E,F);A.wj_root.after(A.log_delay_ms,A.process_log_queue)
	def render_log(A,text,round_start,is_win,is_loss,is_push):E=is_push;D=is_loss;C=is_win;B=round_start;F=Label(A.log_frame,text=text,font=A.styles[_D],bg=A.colour_scheme[_AL]if B else A.colour_scheme[_A_]if C else A.colour_scheme[_B1]if D else A.colour_scheme['push_bg']if E else A.colour_scheme[_Ay],fg=A.colour_scheme[_AM]if B else A.colour_scheme[_B0]if C else A.colour_scheme[_B2]if D else A.colour_scheme['push_fg']if E else A.colour_scheme[_Az],bd=2,relief=_BK,padx=6,pady=4,wraplength=400,anchor=_G,justify=_M);F.pack(fill=_F,pady=4,padx=6);A.wj_root.update_idletasks();A.log_canvas.yview_moveto(_U)
	def return_balance(A):
		B=A.dbm.fetch_user_balance(A.user_data[_K])
		if not B[_I]:A.return_to_menu(is_error=_A,error=Exception(_Af))
		if B[_H]is not _C:return B[_H]
		else:A.return_to_menu(is_error=_A,error=Exception("Fetched balance returns 'None'"));return 0
	def check_balance(A):
		if A.return_balance()==0:
			if A.user_data.get(_Z):messagebox.showinfo(_B4,'Your balance is £0. As an administrator, you can set a new balance.');A.admin_modify_bet(A.wj_root);return _A
			else:messagebox.showinfo(_B4,'Your balance is now £0. Given that you have no more money, your account will be terminated.');A.dbm.terminate_user_account(A.user_data[_K],'Balance reached £0');A.return_to_menu();return _B
		return _A
	def modify_user_balance(A,balance):B=balance;A.dbm.modify_user_balance(A.user_data[_K],B);A.balance_label.config(text=f"Balance: £{B}");A.log_message(text=f"You have a total of £{B} in your account.")
	def start_round(A):
		D='Invalid bet'
		if A.round_active:return
		A.check_balance()
		try:B=int(A.bet_var.get())
		except ValueError:messagebox.showerror(D,'Bet must be a number.');return
		C=A.return_balance()
		if B<=0 or B>C:messagebox.showerror(D,f"You must bet between £1 and £{C}.");return
		A.log_message(text='Starting new round...',round_start=_A);A.current_bet=B;A.modify_user_balance(C-B);A.player_hand.clear();A.dealer_hand.clear();A.deck=CasinoDeckManager(shuffle=_A,game_mode=_BL);A.log_message(text='The deck is being shuffled...');A.player_hand.extend([A.deck.draw(1),A.deck.draw(1)]);A.dealer_hand.extend([A.deck.draw(1),A.deck.draw(1)]);A.round_active=_A;A.update_button_states();A.logs_after_deal()
	def logs_after_deal(A):B=A.deck.blackjack_hand_value(A.player_hand);A.log_message(text=f"You are given the cards {A.deck.treys_to_pretty(A.player_hand[0])}, {A.deck.treys_to_pretty(A.player_hand[1])} with a total value of {B}.");A.log_message(text=f"{A.dealer} has been dealt their cards. The dealer shows {A.deck.treys_to_pretty(A.dealer_hand[0])} with a total value of {A.deck.blackjack_hand_value([A.dealer_hand[0]])}.");A.log_message(text=f"{A.dealer} then motions for you to make your move.")
	def resolve_dealer(A):
		A.log_message(text=f"{A.dealer} reveals their hidden card: {A.deck.treys_to_pretty(A.dealer_hand[1])} with the hand value of {A.deck.blackjack_hand_value(A.dealer_hand)}.")
		while A.deck.blackjack_hand_value(A.dealer_hand)<17:A.log_message(text=f"Given that {A.dealer}'s hand value is less than 17, they must hit.");A.dealer_hand.append(A.deck.draw(1));A.log_message(text=f"{A.dealer} draws {A.deck.treys_to_pretty(A.dealer_hand[-1])}, bringing their hand value to {A.deck.blackjack_hand_value(A.dealer_hand)}.")
		C=A.deck.blackjack_hand_value(A.player_hand);B=A.deck.blackjack_hand_value(A.dealer_hand)
		if C==21 and len(A.player_hand)==2:A.log_message(text='You have WhiteJoe!');D=A.return_balance();D+=int(A.current_bet*2.5);A.modify_user_balance(D);A.end_round(win=_A);return
		if B>21 or C>B:
			if B>21:A.log_message(text=f"{A.dealer} has busted!")
			if C>B:A.log_message(text="Your hand is higher than the dealer's!")
			A.end_round(win=_A)
		elif C==B:A.end_round(push=_A)
		else:
			if B<=21 and B>C:A.log_message(text=f"{A.dealer}'s hand is higher than yours.")
			A.end_round(loss=_A)
	def end_round(A,*,win=_B,loss=_B,push=_B):
		C=A.dbm.fetch_user_balance(A.user_data[_K]);B=C[_H]if C[_I]else 0
		if win:B+=A.current_bet*2;A.log_message(text="Congrats! You've won this round.",is_win=_A)
		elif loss:A.log_message(text="You've lost this round. Better luck next time.",is_loss=_A);A.log_message(text='Did you know that most gambling losses are due to chasing losses? Remember to gamble responsibly!')
		elif push:A.log_message(text='You and the dealer have the same hand. Therefore you tie and your bet is returned to you.',is_push=_A);B+=A.current_bet;A.log_message(text=f"You have a total of £{B} to your disposal.")
		A.modify_user_balance(B);A.current_bet=0;A.current_bet_label.config(text=_Ag);A.round_active=_B;A.update_button_states()
		for D in A.action_buttons:D.config(state=_W)
	def return_to_menu(A,is_error=_B,error=_C):
		if is_error:messagebox.showerror(_L,f"{error}, exiting game.")
		A.wj_root.destroy();Casino_Interface(administrator=_A if A.user_data.get(_Z)else _B,user_data=A.user_data)
	def hit(A):
		if not A.round_active:return
		A.log_message(text="You've chosen to hit.");A.player_hand.append(A.deck.draw(1));B=A.deck.blackjack_hand_value(A.player_hand);A.log_message(text=f"You draw {A.deck.treys_to_pretty(A.player_hand[-1])}.");C=', '.join(A.deck.treys_to_pretty(B)for B in A.player_hand);A.log_message(text=f"You have the cards {C} totaling {B}.")
		if B>21:A.log_message(text='You busted!');A.end_round(loss=_A)
		else:A.log_message(text='You may choose to hit again or stand.')
	def stand(A):
		if not A.round_active:return
		A.log_message(text="You've chosen to stand.");A.resolve_dealer()
	def double_down(A):
		if not A.round_active:return
		A.log_message(text="You've chosen to double down.");B=A.dbm.fetch_user_balance(A.user_data[_K])
		if not B[_I]:A.return_to_menu(is_error=_A,error=Exception(_Af));return
		C=B[_H]
		if C<A.current_bet:messagebox.showerror('Cannot double down','Not enough balance to double down.');return
		A.log_message(text=f"Doubling your bet from £{A.current_bet} to £{A.current_bet*2}.");A.modify_user_balance(C-A.current_bet);A.current_bet*=2;A.player_hand.append(A.deck.draw(1));D=A.deck.blackjack_hand_value(A.player_hand);A.log_message(text=f"You draw {A.deck.treys_to_pretty(A.player_hand[-1])}.");E=', '.join(A.deck.treys_to_pretty(B)for B in A.player_hand);A.log_message(text=f"You have the cards {E} totaling {D}.")
		if D>21:A.end_round(loss=_A)
		else:A.resolve_dealer()
	def surrender(A):
		if not A.round_active:return
		A.log_message(text="You've chosen to surrender.");B=A.dbm.fetch_user_balance(A.user_data[_K]);D=B[_H]if B[_I]else 0;C=A.current_bet//2;A.modify_user_balance(D+C);A.log_message(text=f"You get back £{C} from your bet of £{A.current_bet}.");A.current_bet=0;A.current_bet_label.config(text=_Ag);A.round_active=_B;A.update_button_states()
TIME_OUT=1000
MIN_RAISE_FACTOR_LOW_DIFF=.5
MAX_RAISE_FACTOR_LOW_DIFF=2.
MIN_RAISE_FACTOR_HIGH_DIFF=.75
MAX_RAISE_FACTOR_HIGH_DIFF=3.
EXPERIENCE_THRESHOLD=50
DEFAULT_DELTA=.05
MAX_OUTS=20
FOLD_BIAS_MAX=.4
FOLD_BIAS_MIN=.04
class PokerPlayer:
	def __init__(A,*,user_id=_C,is_bot=_B,difficulty=_C):
		A.user_id=user_id;A.is_bot=bool(is_bot);A.difficulty=difficulty;A.dm=CasinoDeckManager(game_mode=_A7)
		if not A.is_bot:A.init_player()
		else:A.init_bot()
		A.active_range=A.base_range.copy()
	def init_player(A):
		if not A.user_id:raise ValueError('user_id is required for human players.')
		A.dbm=DatabaseManagement();B=A.dbm.load_user_poker_data(A.user_id)
		if B is _C:raise ValueError(f"Failed to load poker data for user_id={A.user_id}")
		A.record=B;A.vpip=B['vpip'];A.pfr=B['pfr'];A.aggression_factor=A.pfr/max(_U,A.vpip);A.fold_to_raise=B[_A2];A.call_when_weak=B[_A3];A.stats={_a:B[_a],_w:B[_w]};C=B[_AQ]
		if A.stats[_a]<=EXPERIENCE_THRESHOLD:A.base_range=generate_range_chart();A.stored_range=C if C else generate_range_chart()
		else:A.base_range=C if C else generate_range_chart();A.stored_range=A.base_range
		A.bot_characteristics=_C
	def init_bot(A):
		if A.difficulty is _C:raise ValueError('difficulty is required for bot players.')
		A.dbm=_C;A.record=_C;A.vpip=difficulty_curve(A.difficulty,35,18);A.pfr=difficulty_curve(A.difficulty,10,20);A.aggression_factor=A.pfr/max(_U,A.vpip);A.bluff_freq=difficulty_curve(A.difficulty,.15,.4);A.fold_to_raise=difficulty_curve(A.difficulty,.6,.3);A.call_when_weak=difficulty_curve(A.difficulty,.5,.2);A.base_range=generate_bot_range(A.vpip,A.difficulty);A.stats={_a:0,_w:0};A.bot_characteristics=BotCharacteristics(A.difficulty)
	def decide(B,*,player_hand,community_cards,opponents,pot,to_call,balance,street):A=opponents;C=[A.active_range for A in A];D=len(A);return make_decision(player_hand=player_hand,player_range=B.active_range,community_cards=community_cards,opponent_ranges=C,opponents=A,opponent_count=D,pot=pot,balance=balance,to_call=to_call,bot=B.bot_characteristics,street=street)
	def refresh_from_db(A):
		if A.is_bot or not A.dbm or A.user_id is _C:return
		B=A.dbm.load_user_poker_data(A.user_id)
		if not B:return
		A.record=B;A.vpip=B['vpip'];A.pfr=B['pfr'];A.aggression_factor=A.pfr/max(_U,A.vpip);A.fold_to_raise=B[_A2];A.call_when_weak=B[_A3];A.stats.update({_a:B[_a],_w:B[_w]});C=B.get(_AQ)
		if C:A.base_range=C;A.stored_range=C;A.active_range=C.copy()
	def reset_active_range(A):A.active_range=A.base_range.copy()
	def fetch_player_info(A):return{'record':A.record,_J:A.user_id,_S:A.is_bot,_BO:A.difficulty,'vpip':A.vpip,'pfr':A.pfr,'aggression_factor':A.aggression_factor,_A2:A.fold_to_raise,_A3:A.call_when_weak,_a:A.stats[_a]}
	def __repr__(A):
		if A.is_bot:return f"PokerPlayer(bot, difficulty={A.difficulty}, VPIP={A.vpip:.1f}%, PFR={A.pfr:.1f}%)"
		return f"PokerPlayer(user_id={A.user_id}, VPIP={A.vpip:.1f}%, PFR={A.pfr:.1f}%, Rounds Played={A.stats[_a]})"
class BotCharacteristics:
	def __init__(A,difficulty):B=difficulty;A.is_bot=_A;A.difficulty=B;A.simulations=int(difficulty_curve(B,500,15000));A.noise_level=difficulty_curve(B,.3,.02);A.bluff_multiplier=difficulty_curve(B,.6,1.6);A.risk_tolerance=difficulty_curve(B,.85,1.5);A.mdf_threshold=difficulty_curve(B,.9,.3);A.range_adherence=difficulty_curve(B,.6,.95);A.fold_bias=difficulty_curve(B,FOLD_BIAS_MAX,FOLD_BIAS_MIN)
	def __repr__(A):return f"BotCharacteristics(difficulty={A.difficulty}, simulations={A.simulations}, noise={A.noise_level:.3f}, bluff_mult={A.bluff_multiplier:.2f}, risk_tolerance={A.risk_tolerance:.2f}, mdf_threshold={A.mdf_threshold:.2f}, fold_bias={A.fold_bias:.3f})"
def generate_range_chart():
	D={};E=_B5
	for(F,A)in enumerate(E[::-1]):
		for(G,B)in enumerate(E[::-1]):
			if F<G:C=A+B+_n
			elif F>G:C=B+A+'o'
			else:C=A+B
			D[C]=_V
	return D
def hand_strength_rank(hand):
	A=hand;B=_B5
	if len(A)==2:return 100+B.index(A[0])
	C=B.index(A[0])*10+B.index(A[1])
	if A.endswith(_n):C+=5
	return C
def generate_bot_range(vpip_target,difficulty):B=difficulty_curve(difficulty,.7,2.3);A=sorted(generate_range_chart().keys(),key=lambda h:hand_strength_rank(h)**B,reverse=_A);C=int(len(A)*vpip_target/100);return{B:_U if A<C else _V for(A,B)in enumerate(A)}
def validate_hand_notation(hand):
	A=hand;B=_B5
	if len(A)==2:return A[0]in B and A[0]==A[1]
	if len(A)==3:return A[0]in B and A[1]in B and A[2]in(_n,'o')and A[0]!=A[1]
	return _B
def update_range(chart,action,hand,delta=DEFAULT_DELTA):
	D=delta;C=action;B=hand
	if not validate_hand_notation(B):raise ValueError(f"Invalid hand notation: {B}")
	A=chart.copy()
	if C==_h:A[B]=min(_U,A.get(B,0)+D)
	elif C==_x:A[B]=max(_V,A.get(B,0)-D)
	elif C==_d:A[B]=min(_U,A.get(B,0)+D*.5)
	E=sum(A.values())
	if E>0:A={A:B/E for(A,B)in A.items()}
	return A
def difficulty_curve(level,low,high):A=max(_V,min(_U,level/1e2));return low+(high-low)*A
def apply_noise(value,bot):B=max(_V,_U-bot.difficulty/1e2);A=bot.noise_level*B;C=random.uniform(-A,A);return max(_V,min(_U,value+C))
def describe_hand(player_hand,community_cards):
	A=CasinoDeckManager(game_mode=_A7)
	try:return str(A.evaluate_hand(player_hand,community_cards))
	except Exception as B:print(B);return'Unknown'
def build_rank_index(available):
	A={}
	for B in available:A.setdefault(B[0],[]).append(B)
	return A
def hand_equity(player_hand,community_cards,opponent_range,bot=_C):
	F=community_cards
	if bot is _C:return .5
	Q=calculate_simulation_count(_Ah if len(F)==5 else _A0,bot.difficulty);B=CasinoDeckManager(shuffle=_B,game_mode=_A7);B.deck.cards=list(CasinoDeckManager(shuffle=_A).deck.cards);G=[B.str_to_treys(A)for A in player_hand];D=[B.str_to_treys(A)for A in F]
	for R in G+D:B.remove_card(R)
	H=[(B,A)for(B,A)in opponent_range.items()if A>0]
	if not H:return .5
	S,T=zip(*H);I=J=C=0;E=5-len(D)
	for K in range(Q):
		if K>0 and K%TIME_OUT==0 and C==0:return .5
		A=B.copy();A.deck.cards=A.deck.cards[:];random.shuffle(A.deck.cards)
		if E>0:L=A.deck.cards[:E];A.deck.cards=A.deck.cards[E:]
		else:L=[]
		M=D+L
		try:N=A.evaluator.evaluate(G,M)
		except Exception:continue
		U=random.choices(S,weights=T,k=1)[0];V=A.str_deck();W=build_rank_index(V);O=notation_to_cards_with_index(U,W,A)
		if O is _C:continue
		try:P=A.evaluator.evaluate(O,M)
		except Exception:continue
		C+=1
		if N<P:I+=1
		elif N==P:J+=1
	if C==0:return .5
	return max(_V,min(_U,(I+J*.5)/C))
def notation_to_cards_with_index(hand_notation,rank_index,dm):
	B=rank_index;A=hand_notation
	if len(A)==2:
		F=B.get(A[0],[])
		if len(F)<2:return
		G=random.sample(F,2);return[dm.str_to_treys(A)for A in G]
	H,I,J=A;C=B.get(H,[]);D=B.get(I,[])
	if not C or not D:return
	if J==_n:E=[(A,B)for A in C for B in D if A[1]==B[1]]
	else:E=[(A,B)for A in C for B in D if A[1]!=B[1]]
	if not E:return
	K,L=random.choice(E);return[dm.str_to_treys(K),dm.str_to_treys(L)]
def notation_to_specific_cards(hand_notation,dm):
	A=dm.str_deck()
	if not A:return
	B=build_rank_index(A);return notation_to_cards_with_index(hand_notation,B,dm)
def calculate_simulation_count(street,difficulty):
	B=street;A=int(difficulty_curve(difficulty,500,15000))
	if B==_A0:return max(100,A//4)
	elif B==_AN:return max(200,A//2)
	elif B==_Ai:return max(300,int(A/1.5))
	return A
def collective_hand_equity(player_hand,community_cards,opponent_ranges,opponent_count,bot=_C):
	A=opponent_ranges
	if not A:return _V
	B=_U
	for C in A:B*=hand_equity(player_hand,community_cards,C,bot)
	return B
def pot_odds(current_pot,call_amount):
	A=call_amount
	if A<=0:return _V
	return A/(A+current_pot)
def expected_value_of_call(pot,call_amount,equity):A=equity;return A*pot-(1-A)*call_amount
def estimate_outs(player_hand,community_cards):
	D=community_cards;C=player_hand
	def J(rank):return{'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,'T':10,'J':11,'Q':12,'K':13,'A':14}[rank]
	E=C+D;K=[A[0]for A in E];F=[A[1]for A in E];A=0
	for L in set(F):
		if F.count(L)==4:A+=9
	G=sorted(set(J(A)for A in K))
	for B in combinations(G,min(4,len(G))):
		if len(B)<4:continue
		H,I=min(B),max(B)
		if I-H==3:A+=8
		elif I-H==4:A+=4
	M=[A[0]for A in D]
	for N in C:
		if N[0]not in M:A+=2
	return min(A,MAX_OUTS)
def probability_to_hit_by_river(outs,cards_remaining,cards_to_come):
	B=cards_remaining
	if outs<=0 or B<=0:return _V
	C=_U;A=B
	for D in range(cards_to_come):
		if A<=0:break
		C*=(A-outs)/A;A-=1
	return _U-C
def minimum_defense_frequency(bet,pot):
	if bet<=0:return _V
	return pot/(pot+bet)
def optimal_bluff_ratio(pot,bet):
	A=bet
	if A<=0 or pot<=0:return _V
	return A/(pot+A)
def should_bluff_call(pot,to_call,equity,opponent_fold_to_raise,bot):
	A=to_call
	if equity>pot_odds(pot,A)*1.2:return _B
	B=optimal_bluff_ratio(pot,A);C=B*bot.bluff_multiplier*opponent_fold_to_raise;return random.random()<C
def should_bluff_raise(pot,raise_amount,equity,opponent_fold_to_raise,bot):
	if equity>.6:return _B
	A=optimal_bluff_ratio(pot,raise_amount);B=A*bot.bluff_multiplier*opponent_fold_to_raise*1.5;return random.random()<B
def calculate_raise_amount(pot,equity,balance,bot):
	A=pot
	if bot.difficulty>=80:C=A*MIN_RAISE_FACTOR_HIGH_DIFF;B=A*MAX_RAISE_FACTOR_HIGH_DIFF
	else:C=A*MIN_RAISE_FACTOR_LOW_DIFF;B=A*MAX_RAISE_FACTOR_LOW_DIFF
	B=min(B,balance);D=C+(B-C)*equity;return int(D/5)*5
def cards_to_notation(player_hand):
	C=player_hand;F=_B5;A,D=C[0][0],C[0][1];B,E=C[1][0],C[1][1]
	if F.index(A)<F.index(B):A,B=B,A;D,E=E,D
	if A==B:return A+B
	return A+B+(_n if D==E else'o')
def make_decision(player_hand,player_range,community_cards,opponent_ranges,opponents,opponent_count,pot,balance,to_call,bot,street):
	P=player_range;L=street;K=community_cards;I=opponents;H=player_hand;E=to_call;D=pot;C=balance;B=bot;N=max(_V,_U-B.difficulty/1e2)
	if L==_A0 and P is not _C:
		Q=cards_to_notation(H);O=P.get(Q,_V)
		if O==_V:
			if random.random()>_U-B.range_adherence:0
			else:return(_x,)if E>0 else(_d,)
		R=.5+O*.5
	else:Q=_C;O=.5;R=_U
	A=collective_hand_equity(H,K,opponent_ranges,opponent_count,B);A=apply_noise(A,B);A*=R;A*=B.risk_tolerance
	if random.random()<N:A*=random.uniform(.5,.9)
	if L==_Ah:
		S=describe_hand(H,K)
		if B.difficulty>=85 and B.risk_tolerance>=_U:
			if S in('Straight Flush','Four of a Kind','Full House'):F=calculate_raise_amount(D,A,C,B);return _h,F
	else:S=_C
	V=pot_odds(D,E);W=expected_value_of_call(D,E,A)
	if L in(_AN,_Ai):X=estimate_outs(H,K);Y=52-len(H)-len(K);Z=2 if L==_AN else 1;a=probability_to_hit_by_river(X,Y,Z);A=max(A,a)
	if A>.65 and C>0:
		F=calculate_raise_amount(D,A,C,B)
		if 0<F<=C:return _h,F
	if B.difficulty>=50 and W>0:return _d,
	b=minimum_defense_frequency(E,D)*B.mdf_threshold
	if A>=V:
		T=b
		if random.random()<N:T*=random.uniform(.3,.8)
		if random.random()<T:return _d,
	if I:M=sum(A.fold_to_raise for A in I)/len(I);U=sum(A.call_when_weak for A in I)/len(I)
	else:M=.5;U=.5
	J=_B;G=_C
	if A<.4:
		if should_bluff_raise(D,E*3,A,M,B):
			if M>U:J=_A;G=_h
			elif random.random()<.3:J=_A;G=_h
	elif .2<A<.5:
		if should_bluff_call(D,E,A,M,B):J=_A;G=_d
	if random.random()<N:J=random.choice([_A,_B]);G=random.choice([_h,_d])
	if J:
		if G==_h:F=calculate_raise_amount(D,A,C,B);return _h,F if F<=C else int(C)
		elif G==_d and E<=C:return _d,
	if E<=C and random.random()<B.fold_bias:return _d,
	return _x,
DEFAULT_BOT_ROSTER=['Angus','Angeban','Grey','Mr Rhodes','Leon S. Kennedy','Ada Wong','Albert Wesker','Jack Krauser','Luis Serra','Nathan Drake','Joel Miller','Tobias Rieper','Arthur Morgan','Dutch Van Der Linde','Jin Sakai','Atsu Onryo','Alfred','Danny Trejo','Bagley','Sauron','Morgoth','Han Solo','Gordon Freeman','Mr Chips','Dante from Devil May Cry','Cal Kestis','Master Chief','Lara Croft','Vector the Crocodile','Rayman','Hideo Kojima','Naked Snake','Big Boss','Venom Snake','Liquid Snake','Solidus Snake','Archimedes','Giancarlo Esposito','Kinji Hakari','Toji Fushiguro','Jon Snow','Pikmin','Hatsune Miku','Oggdo Bogdo','Spawn of Oggdo']
WIN_CRITERIA_ELIMINATE_ALL=_BH
WIN_CRITERIA_EARN_TARGET=_Au
WIN_CRITERIA_SURVIVE_ROUNDS=_Bs
WIN_CRITERIA_LAST_MAN_BLIND=_Bt
class TournamentManager:
	def __init__(A,settings):B=settings;A.total_rounds=B.get(_Ab,5);A.total_players=B.get(_Ac,4);A.win_criteria=B.get(_At,WIN_CRITERIA_ELIMINATE_ALL);A.target_amount=B.get(_Ad,1000);A.base_small_blind=B.get(_AE,50);A.base_big_blind=B.get(_AF,100);A.current_round=1;A.rounds_survived=0;A.human_chips_at_round_start=0;A.round_wins=0;A.tournament_over=_B;A.tournament_won=_B
	@property
	def current_small_blind(self):
		A=self
		if A.win_criteria==WIN_CRITERIA_LAST_MAN_BLIND:return A.base_small_blind*2**(A.current_round-1)
		B=max(1,(A.current_round-1)//3);return int(A.base_small_blind*1.5**B)
	@property
	def current_big_blind(self):
		A=self
		if A.win_criteria==WIN_CRITERIA_LAST_MAN_BLIND:return A.base_big_blind*2**(A.current_round-1)
		B=max(1,(A.current_round-1)//3);return int(A.base_big_blind*1.5**B)
	def record_round_start(A,human_balance):A.human_chips_at_round_start=human_balance
	def evaluate_round_win(A,human_player,all_players):
		B=human_player
		if A.win_criteria==WIN_CRITERIA_ELIMINATE_ALL:C=[A for A in all_players if A[_S]and A[_N]not in(_i,_T)];return len(C)==0
		if A.win_criteria==WIN_CRITERIA_EARN_TARGET:return B[_H]>=A.target_amount
		if A.win_criteria in(WIN_CRITERIA_SURVIVE_ROUNDS,WIN_CRITERIA_LAST_MAN_BLIND):return B[_N]!=_T
		return _B
	def advance_round(A,human_won_round):
		C=human_won_round
		if C:A.round_wins+=1
		A.rounds_survived+=1;A.current_round+=1
		if A.current_round>A.total_rounds:A.tournament_over=_A;A.tournament_won=A.round_wins>0;B=f"Tournament complete!\nYou won {A.round_wins} of {A.total_rounds} rounds.\n";B+='🏆 Tournament Victory!'if A.tournament_won else'Better luck next time.';return{_BP:_A,_BQ:A.tournament_won,_B6:B}
		D={WIN_CRITERIA_ELIMINATE_ALL:_Bu,WIN_CRITERIA_EARN_TARGET:f"Earn £{A.target_amount}",WIN_CRITERIA_SURVIVE_ROUNDS:'Survive the round',WIN_CRITERIA_LAST_MAN_BLIND:'Survive as blinds escalate'}.get(A.win_criteria,'');B=f"Round {A.current_round-1} complete.  {'Round won! ✓'if C else'Round lost.'}\nRound {A.current_round} of {A.total_rounds}.\nWin criteria: {D}\nBlinds: £{A.current_small_blind} / £{A.current_big_blind}";return{_BP:_B,_BQ:_B,_B6:B}
	def fetch_status_text(A):
		if not A.tournament_over:return f"Tournament  |  Round {A.current_round}/{A.total_rounds}  |  Wins: {A.round_wins}  |  Blinds: £{A.current_small_blind} / £{A.current_big_blind}"
		return f"Tournament Over  |  Wins: {A.round_wins}/{A.total_rounds}"
class HarrogateHoldEm:
	def __init__(A,user_data,settings,bots):
		I='name';D=bots;C=user_data;B=settings;A.user_data=C;A.hhe_root=Tk();A.hhe_root.title("One More Time Casino — Harrogate Hold 'Em")
		try:A.hhe_root.attributes(_AV,_A)
		except Exception:pass
		A.log_queue=[];A.log_active=_B;A.log_delay_ms=int(DELAY*1000);A.bot_decision_queue=Queue();A.bot_thinking=_B;from database_management_and_logging_V6 import DatabaseManagement as J;A.dbm=J()
		if not A.dbm.check_user_poker_data_exists(C[_J]):A.dbm.initialise_user_poker_data(C[_J])
		A.styles=fetch_font_settings(A.hhe_root)
		if D is _C:K=B.get(_m,3);L=B.get(_AG,50);F=list(DEFAULT_BOT_ROSTER);random.shuffle(F);D=[[F[A%len(F)],L]for A in range(K)]
		A.tournament_mode=B.get(_s,_B)
		if A.tournament_mode:A.tournament=TournamentManager(B);A.small_blind_value=A.tournament.current_small_blind;A.big_blind_value=A.tournament.current_big_blind
		else:A.tournament=_C;A.small_blind_value=B.get(_AE,50);A.big_blind_value=B.get(_AF,100)
		A.bots={}
		for(E,H)in enumerate(D[:B.get(_m,len(D))]):A.bots[E]={I:H[0],_BO:H[1]}
		A.players=[];G=_C
		if A.user_data.get(_J):
			try:G=PokerPlayer(user_id=A.user_data[_J],is_bot=_B)
			except Exception as M:messagebox.showerror(_L,f"Failed to initialise player model: {M}");G=_C
		A.players.append({_Q:C[_K]+' (You)',_Aj:_C,_j:[],_H:A.return_balance(),_R:0,_N:_A1,_S:_B,_J:A.user_data[_J],_p:G});A.current_round_number=1;A.actions_logged=[]
		for E in range(B.get(_m,len(A.bots))):A.players.append({_Q:A.bots[E][I],_Aj:_C,_j:[],_H:B.get(_Aa,1000),_R:0,_N:_A1,_S:_A,_J:_C,_p:PokerPlayer(is_bot=_A,difficulty=max(0,A.bots[E][_BO]))})
		random.shuffle(A.players)
		for(N,O)in enumerate(A.players,start=1):O[_Aj]=N
		A.player_count=len(A.players);A.player_go=_C;A.initial_position=-1;A.current_position=0;A.action_position=0;A.small_blind_player=_C;A.big_blind_player=_C;A.current_bet=0;A.pot_size=0;A.player_turn=_B;A.round_active=_B;A.round_number=1;A.street='';A.board=[[],[]];A.flop=[[],[]];A.turn=[[],[]];A.river=[[],[]];A.main_frame=Frame(A.hhe_root);A.main_frame.pack(expand=_A,fill=_b,padx=10,pady=10);A.action_buttons=[];A.colour_scheme={_q:'#ddd3bc',_B7:'#e6dcc6',_AJ:'#2e7d73',_f:'#286b62',_Ax:'#5b2a3c',_Y:'#6a2e4f',_AK:'#141414',_O:'#f2f2f2',_A8:'#1e1e1e',_Ay:'#1a1a1a',_Az:'#cfcfcf',_AL:'#243b7a',_AM:_Ae,_A_:'#244d3a',_B0:'#a8e6c1',_B1:'#4a1e1e',_B2:'#f2a3a3',_BM:'#5c4a10',_BN:'#f0d898',_C1:'#3c2a4a',_C2:'#d4b8e8',_BR:'#4a1e38',_BS:'#e8b8d0'};set_view(A,A.harrogate_hold_em_screen);A.check_bot_decision_queue()
	def run(A):A.hhe_root.mainloop()
	def harrogate_hold_em_screen(A,frame):
		C=frame;B=A.colour_scheme;C.columnconfigure(0,weight=2);C.columnconfigure(1,weight=1);C.rowconfigure(0,weight=1);C.rowconfigure(1,weight=1);C.rowconfigure(2,weight=1);D=Frame(C,bd=2,relief=_z,bg=B[_q]);D.grid(column=0,row=0,sticky=_t,padx=5,pady=5);A.round_number_label=Label(D,bg=B[_q],fg=B[_A8],anchor=_G,font=A.styles[_D]);A.round_number_label.pack(fill=_F,padx=10,pady=5);A.board_label=Label(D,bg=B[_q],fg=B[_A8],anchor=_G,font=A.styles[_D]);A.board_label.pack(fill=_F,padx=10,pady=5);A.player_blinds_label=Label(D,bg=B[_q],fg=B[_A8],anchor=_G,font=A.styles[_D]);A.player_blinds_label.pack(fill=_F,padx=10,pady=5);A.pot_size_label=Label(D,bg=B[_q],fg=B[_A8],anchor=_G,font=A.styles[_D]);A.pot_size_label.pack(fill=_F,padx=10,pady=5);A.player_turn_label=Label(D,bg=B[_q],fg=B[_A8],anchor=_G,font=A.styles[_D]);A.player_turn_label.pack(fill=_F,padx=10,pady=5);A.tournament_label=Label(D,font=A.styles[_X],bg=B[_BR],fg=B[_BS],pady=4,padx=6)
		if A.tournament_mode:A.tournament_label.pack(fill=_F,padx=10,pady=4)
		I=Frame(C,bd=2,relief=_z,bg=B[_B7]);I.grid(column=0,row=1,rowspan=2,sticky=_t,padx=5,pady=5);A.log_canvas=Canvas(I,bg=B[_B7],highlightthickness=0);M=Scrollbar(I,orient=_AW,command=A.log_canvas.yview);A.log_canvas.configure(yscrollcommand=M.set);M.pack(side=_A4,fill='y');A.log_canvas.pack(side=_M,fill=_b,expand=_A);A.log_frame=Frame(A.log_canvas,bg=B[_B7]);A.log_window=A.log_canvas.create_window((0,0),window=A.log_frame,anchor='nw');A.log_canvas.bind(_y,lambda e:A.log_canvas.itemconfig(A.log_window,width=e.width));A.log_frame.bind(_y,lambda e:A.log_canvas.configure(scrollregion=A.log_canvas.bbox('all')));J=Frame(C,bd=2,relief=_z,bg=B[_AJ]);J.grid(row=0,column=1,sticky=_t,padx=5,pady=5);Button(J,text=_B_,font=A.styles[_E],bg=B[_Y],fg=B[_O],relief=_e,bd=0,cursor=_o,command=A.return_to_menu).pack(pady=5);N=0
		if not A.user_data.get(_Z):
			O=A.dbm.fetch_user_balance(A.user_data[_K])
			if not O[_I]:A.return_to_menu(is_error=_A,error=Exception(_Af));return
			N=O[_H]
		else:A.admin_modify_bet(C)
		G=[]
		for K in(f"Username: {A.user_data[_K]}",f"Balance: £{N}",_Ag,f"Blinds: £{A.small_blind_value} / £{A.big_blind_value}"):P=Label(J,text=K,font=A.styles[_D],bg=B[_AJ],fg=B[_O],anchor=_G);P.pack(anchor=_G,pady=5,padx=5);G.append(P)
		A.balance_label=cast(Label,G[1]);A.current_bet_label=cast(Label,G[2]);A.blinds_label=cast(Label,G[3]);E=Frame(C,bd=2,relief=_z,bg=B[_f]);E.grid(row=1,column=1,sticky=_t,padx=5,pady=5);E.columnconfigure(0,weight=1);E.columnconfigure(1,weight=0);E.rowconfigure(0,weight=1);A.players_canvas=Canvas(E,bg=B[_f],highlightthickness=0);A.players_canvas.grid(row=0,column=0,sticky=_t);Q=Scrollbar(E,orient=_AW,command=A.players_canvas.yview);Q.grid(row=0,column=1,sticky='ns');A.players_canvas.configure(yscrollcommand=Q.set);A.players_frame=Frame(A.players_canvas,bg=B[_f]);A.players_window=A.players_canvas.create_window((0,0),window=A.players_frame,anchor='nw');A.players_canvas.bind(_y,lambda e:A.players_canvas.itemconfig(A.players_window,width=e.width));A.players_frame.bind(_y,lambda e:A.players_canvas.configure(scrollregion=A.players_canvas.bbox('all')));A.build_players_panel();F=Frame(C,bd=2,relief=_z,bg=B[_Ax]);F.grid(row=2,column=1,sticky=_t,padx=5,pady=5)
		def R(amount):
			try:B=int(A.bet_var.get())
			except Exception:B=0
			B+=amount;C=A.return_balance()
			if C is not _C:B=max(1,min(B,int(C)))
			A.bet_var.set(str(B));A.current_bet_label.config(text=f"Current Bet: £{B}")
		def T(*D):
			try:
				B=int(A.bet_var.get());B=max(0,B);C=A.return_balance()
				if C is not _C and B>C:B=int(C)
			except Exception:B=0
			A.bet_var.set(str(B));A.current_bet_label.config(text=f"Current Bet: £{B}")
		A.bet_var=StringVar(value='0');A.bet_var.trace_add(_BG,T);Entry(F,textvariable=A.bet_var,width=12,font=A.styles[_D],bg=B[_Y],fg=B[_O],insertbackground=B[_O],relief=_e,bd=4,justify=_B3).pack(pady=(8,6))
		for L in(10,100,1000):H=Frame(F,bg=B[_AK],bd=2,relief='ridge',padx=6,pady=3);H.pack(fill=_F,pady=3);Button(H,text='+',font=A.styles[_E],width=3,bg=B[_Y],fg=B[_O],relief=_e,bd=0,cursor=_o,command=lambda v=L:R(v)).pack(side=_M,padx=4);Label(H,text=str(L),font=A.styles[_D],bg=B[_AK],fg=B[_O],width=8,anchor=_B3).pack(side=_M,expand=_A);Button(H,text='−',font=A.styles[_E],bg=B[_Y],fg=B[_O],relief=_e,bd=0,width=3,cursor=_o,command=lambda v=-L:R(v)).pack(side=_A4,padx=4)
		for(K,U)in(('Raise',A.raise_bet),('Call',A.call),('Fold',A.fold)):S=Button(F,text=K,font=A.styles[_E],bg=B[_Y],fg=B[_O],relief=_e,bd=0,width=18,cursor=_o,command=U,state=_W);S.pack(pady=6);A.action_buttons.append(S)
		A.start_button=Button(F,text=f"Start Round {A.round_number}",font=A.styles[_E],bg=B[_AL],fg=B[_AM],relief=_e,bd=0,width=18,activebackground='#3a52a0',cursor=_o,command=A.check_round);A.start_button.pack(pady=10);A.update_labels();A.update_button_states()
	def build_players_panel(A):
		D='e';B=A.colour_scheme
		for J in A.players_frame.winfo_children():J.destroy()
		Label(A.players_frame,text='Players',font=A.styles[_AB],bg=B[_f],fg=B[_O]).pack(anchor=_G,padx=8,pady=(6,10));Frame(A.players_frame,height=1,bg=B[_Y]).pack(fill=_F,padx=8,pady=2)
		for C in A.players:
			H=Frame(A.players_frame,bg=B[_f]);H.pack(fill=_F,padx=8,pady=4);E=Frame(H,bg=B[_f]);E.pack(side=_M,fill=_F,expand=_A);F=''
			if A.round_active:
				if C is A.small_blind_player:F='  [SB]'
				elif C is A.big_blind_player:F='  [BB]'
				if C[_Aj]-1==A.current_position and C[_N]==_A1:F+='  <'
			Label(E,text=C[_Q]+F,font=A.styles[_D],bg=B[_f],fg=B[_O],anchor=_G,wraplength=180).pack(fill=_F)
			if A.round_active and C[_j]:
				if not C[_S]or A.street==_AO:
					I=' '.join(C[_j][1])if len(C[_j])>1 else''
					if I:Label(E,text=f"Cards:  {I}",font=A.styles[_D],bg=B[_f],fg=B[_O],anchor=_G).pack(fill=_F)
				else:Label(E,text='Cards:  [?]  [?]',font=A.styles[_D],bg=B[_f],fg=B[_O],anchor=_G).pack(fill=_F)
			G=Frame(H,bg=B[_f]);G.pack(side=_A4);Label(G,text=f"£{C[_H]}",font=A.styles[_D],bg=B[_f],fg=B[_O],anchor=D,width=8).pack(anchor=D)
			if C[_R]>0:Label(G,text=f"Bet:  £{C[_R]}",font=A.styles[_D],bg=B[_f],fg=B[_O],anchor=D).pack(anchor=D)
			Label(G,text=C[_N],font=A.styles[_D],bg=B[_f],fg=B[_O],anchor=D).pack(anchor=D);Frame(A.players_frame,height=1,bg=B[_Y]).pack(fill=_F,padx=8,pady=2)
	def update_ui(A):A.update_labels();A.update_button_states();A.update_player_status()
	def update_labels(A):
		if not getattr(A,_BT,_C)or not A.balance_label.winfo_exists():return
		A.balance_label.config(text=f"Balance: £{A.return_balance()}")
		if getattr(A,'blinds_label',_C)and A.blinds_label.winfo_exists():A.blinds_label.config(text=f"Blinds: £{A.small_blind_value} / £{A.big_blind_value}")
		if getattr(A,'tournament_label',_C)and A.tournament_label.winfo_exists():
			if A.tournament_mode and A.tournament:A.tournament_label.config(text=A.tournament.fetch_status_text())
		if not getattr(A,'round_number_label',_C)or not A.round_number_label.winfo_exists():return
		if not A.round_active:
			A.round_number_label.config(text=_BI+('  —  TOURNAMENT'if A.tournament_mode else''))
			if A.tournament_mode and A.tournament:B=f"Tournament Round {A.tournament.current_round}/{A.tournament.total_rounds}"
			else:B='Casual mode.'
			A.board_label.config(text=B);A.player_blinds_label.config(text='');A.pot_size_label.config(text='Waiting for round to commence…');A.player_turn_label.config(text='');return
		A.round_number_label.config(text=f"Round {A.round_number}")
		if A.street==_A0:A.board_label.config(text='The Board:  |?|  |?|  |?|  |?|  |?|')
		elif A.street==_AN:A.board_label.config(text=f"The Board:  {' '.join(str(A)for A in A.flop[1])}  |?|  |?|")
		elif A.street==_Ai:C=A.flop[1]if isinstance(A.flop,list)else[];D=A.turn[1]if isinstance(A.turn,list)else[];A.board_label.config(text=f"The Board:  {' '.join(str(A)for A in C+D)}  |?|")
		elif A.street in(_Ah,_AO):A.board_label.config(text=f"The Board:  {' '.join(str(A)for A in A.board[1])}")
		else:A.board_label.config(text='')
		if A.small_blind_player and A.big_blind_player:A.player_blinds_label.config(text=f"Small Blind: {A.small_blind_player[_Q]}  |  Big Blind: {A.big_blind_player[_Q]}")
		A.pot_size_label.config(text=f"Pot: £{A.pot_size}")
		if A.street==_AO:A.player_turn_label.config(text=_C3)
		elif A.player_go and A.street:A.player_turn_label.config(text=f"It is {A.player_go}'s turn.")
		else:A.player_turn_label.config(text='')
	def update_button_states(A):
		A.start_button.config(state=_W if A.round_active else _k)
		if A.round_active and A.player_turn:
			B=next((A for A in A.players if not A[_S]),_C)
			if B:
				C=max(0,A.current_bet-B[_R]);D=max(A.current_bet-B[_R]+A.big_blind_value,A.big_blind_value);E=_k if D<=B[_H]else _W;A.action_buttons[0].config(text=f"Raise  (min £{D})",state=E)
				if C==0:A.action_buttons[1].config(text='Check',state=_k)
				else:A.action_buttons[1].config(text=f"Call  £{C}",state=_k if C<=B[_H]else _W)
				A.action_buttons[2].config(state=_k)
			else:
				for F in A.action_buttons:F.config(state=_W)
		else:A.action_buttons[0].config(text='Raise',state=_W);A.action_buttons[1].config(text='Call',state=_W);A.action_buttons[2].config(text='Fold',state=_W)
	def update_player_status(A):A.build_players_panel()
	def reset_players(B):
		for A in B.players:
			B.modify_player(A,cards=[],refresh_player_model=_A)
			if A[_N]!=_T:A[_N]=_A1
			A[_R]=0
	def modify_player(E,player,cards=_C,change_balance=_C,bet=_C,status=_C,refresh_player_model=_B):
		D=status;C=change_balance;B=cards;A=player
		if A is _C:return
		if B is not _C:A[_j]=E.deck.treys_other(B)if B else B
		if C is not _C:A[_H]+=C
		if bet is not _C:A[_R]=bet
		if D is not _C:A[_N]=D
		if refresh_player_model and not A[_S]and A[_p]:A[_p].refresh_from_db();A[_p].reset_active_range()
	def player_decision(A):A.player_turn=_A;A.update_ui()
	def admin_modify_bet(A,frame):
		B=Toplevel(frame);B.title('Set Starting Balance');B.grab_set();B.protocol(_An,lambda:_C);B.configure(bg=A.colour_scheme[_q]);Label(B,text=_C0,font=A.styles[_D],bg=A.colour_scheme[_q],fg=A.colour_scheme[_O]).pack(pady=8);D=Entry(B,width=20,font=A.styles[_D],bg=A.colour_scheme[_Y],fg=A.colour_scheme[_O],insertbackground=A.colour_scheme[_O]);D.pack(pady=5);E=Label(B,text='',font=A.styles[_X],fg='#e08080',bg=A.colour_scheme[_q]);E.pack(pady=4)
		def C():
			try:
				C=int(D.get().strip())
				if C<0:raise ValueError
				A.balance_label.config(text=f"Balance: £{C}");B.destroy();A.dbm.modify_user_balance(A.user_data[_K],C)
			except Exception:E.config(text='Please enter a valid positive integer.')
		Button(B,text=_Ao,font=A.styles[_E],bg=A.colour_scheme[_Y],fg=A.colour_scheme[_O],relief=_e,bd=0,command=C).pack(pady=10)
	def log_message(A,text,*,round_start=_B,is_win=_B,is_loss=_B,tie=_B,is_thinking=_B,is_tournament=_B):
		A.log_queue.append((text,round_start,is_win,is_loss,tie,is_thinking,is_tournament))
		if not A.log_active:A.process_log_queue()
	def process_log_queue(A):
		if not getattr(A,_C4,_C)or not A.log_frame.winfo_exists():A.log_queue.clear();A.log_active=_B;return
		if not A.log_queue:A.log_active=_B;return
		A.log_active=_A;B=A.log_queue.pop(0)
		if len(B)==6:C,D,E,F,G,H=B;I=_B
		else:C,D,E,F,G,H,I=B
		A.render_log(C,D,E,F,G,H,I);A.hhe_root.after(A.log_delay_ms,A.process_log_queue)
	def render_log(B,text,round_start,is_win,is_loss,tie,is_thinking,is_tournament=_B):
		G=is_tournament;F=is_thinking;E=is_loss;D=is_win;C=round_start
		if not getattr(B,_C4,_C)or not B.log_frame.winfo_exists():return
		A=B.colour_scheme;H=A[_BR]if G else A[_AL]if C else A[_A_]if D else A[_B1]if E else A[_BM]if tie else A[_C1]if F else A[_Ay];I=A[_BS]if G else A[_AM]if C else A[_B0]if D else A[_B2]if E else A[_BN]if tie else A[_C2]if F else A[_Az];Label(B.log_frame,text=text,font=B.styles[_D],bg=H,fg=I,bd=1,relief=_BK,padx=6,pady=4,wraplength=400,anchor=_G,justify=_M).pack(fill=_F,pady=3,padx=6);B.hhe_root.update_idletasks()
		if getattr(B,'log_canvas',_C)and B.log_canvas.winfo_exists():B.log_canvas.yview_moveto(_U)
	def return_balance(A):
		B=A.dbm.fetch_user_balance(A.user_data[_K])
		if not B[_I]:A.return_to_menu(is_error=_A,error=Exception(_Af));return 0
		if B[_H]is _C:A.return_to_menu(is_error=_A,error=Exception('Fetched balance returned None.'));return 0
		return int(B[_H])
	def check_balance(A,frame):
		if A.return_balance()==0:
			if A.user_data.get(_Z):messagebox.showinfo(_B4,'Your balance is £0. As an administrator you may set a new balance to continue.');A.admin_modify_bet(frame);return _A
			else:messagebox.showinfo(_B4,'Your balance has reached £0.  You will be returned to the main menu.');A.return_to_menu();return _B
		return _A
	def modify_user_balance(A,balance):
		B=balance;A.dbm.modify_user_balance(A.user_data[_K],B)
		try:
			if getattr(A,_BT,_C)and A.balance_label.winfo_exists():A.balance_label.config(text=f"Balance: £{B}")
		except Exception:pass
	def log_player_action_to_db(A,action,bet_size):
		D=bet_size;C=action
		for B in A.players:
			if not B[_S]and B[_J]:
				E=A.dbm.log_player_action(user_id=B[_J],round_number=A.current_round_number,street=A.street,action=C,bet_size=D,pot_size=A.pot_size)
				if E:A.actions_logged.append({'street':A.street,_Ak:C,'bet_size':D})
				break
	def check_round(A):A.round_active=_A;A.log_queue.clear();A.log_active=_B;A.actions_logged=[];A.log_message(f"Starting Round {A.round_number}.",round_start=_A);A.reset_players();A.update_ui();A.play_round()
	def blind_management(A):
		A.initial_position=(A.initial_position+1)%A.player_count
		for C in range(A.player_count):
			B=(A.initial_position+1+C)%A.player_count
			if A.players[B][_N]!=_T:A.small_blind_position=B;A.small_blind_player=A.players[B];break
		for C in range(A.player_count):
			B=(A.small_blind_position+1+C)%A.player_count
			if A.players[B][_N]!=_T:A.big_blind_position=B;A.big_blind_player=A.players[B];break
		for C in range(A.player_count):
			B=(A.big_blind_position+1+C)%A.player_count
			if A.players[B][_N]!=_T:A.current_position=B;break
		A.action_position=A.current_position
		for(D,F)in((A.small_blind_player,A.small_blind_value),(A.big_blind_player,A.big_blind_value)):
			if D is _C:continue
			E=min(F,D[_H]);A.modify_player(D,bet=E,change_balance=-E,status=_u)
		if A.big_blind_player is not _C:A.current_bet=A.big_blind_player[_R]
		if A.small_blind_player is not _C and A.big_blind_player is not _C:A.pot_size+=A.small_blind_player[_R]+A.big_blind_player[_R]
	def distribute_cards(A):
		A.deck=CasinoDeckManager(shuffle=_A,game_mode=_A7)
		for B in A.players:
			if B[_N]!=_T:A.modify_player(B,cards=[A.deck.draw(1),A.deck.draw(1)])
		C=[A.deck.draw(1)for B in range(5)];A.board=A.deck.treys_other(C);A.flop[0],A.flop[1],A.turn[0],A.turn[1],A.river[0],A.river[1]=A.board[0][:3],A.board[1][:3],A.board[0][3:4],A.board[1][3:4],A.board[0][4:],A.board[1][4:]
	def play_round(A):
		if A.tournament_mode and A.tournament:
			A.small_blind_value=A.tournament.current_small_blind;A.big_blind_value=A.tournament.current_big_blind;B=next((A for A in A.players if not A[_S]),_C)
			if B:A.tournament.record_round_start(B[_H])
		A.blind_management();A.distribute_cards()
		for C in A.players:
			if not C[_S]:A.log_message(f"Your cards:  {' '.join(C[_j][1])}");break
		A.update_ui();A.street_sequence=[_A0,_AN,_Ai,_Ah,_AO];A.current_street_index=0;A.next_street()
	def decisions(A):
		for C in range(A.player_count):
			B=A.players[A.current_position]
			if B[_N]not in(_u,_i,_T):
				A.player_go=B[_Q]
				if B[_S]:A.player_turn=_B;A.update_ui();A.start_bot_decision_async(B);return
				else:A.player_turn=_A;A.update_ui();A.log_message("It's your turn to play.");return
			A.current_position=(A.current_position+1)%A.player_count
			if A.current_position==A.action_position and C>0 and A.is_betting_complete():A.advance_street();return
		A.advance_street()
	def start_bot_decision_async(A,player):
		B=player
		if A.bot_thinking:return
		A.bot_thinking=_A;A.log_message(f"{B[_Q]} is thinking…",is_thinking=_A);C=800+B[_p].difficulty/1e2*1700;D=random.uniform(-200,200);E=int(C+D);threading.Thread(target=A.bot_decision_worker,args=(B,E),daemon=_A).start()
	def bot_decision_worker(A,player,min_thinking_ms):
		B=player;import time as C;E=C.time()
		try:
			F=A.bot_decision(B);G=(C.time()-E)*1000;D=max(0,min_thinking_ms-G)
			if D>0:C.sleep(D/1e3)
			A.bot_decision_queue.put((B,F,_C))
		except Exception as H:A.bot_decision_queue.put((B,_C,H))
	def check_bot_decision_queue(A):
		try:
			B,D,C=A.bot_decision_queue.get_nowait();A.bot_thinking=_B
			if C:A.bot_error(B,C)
			else:A.execute_bot_decision(B,D)
			A.update_ui();A.current_position=(A.current_position+1)%A.player_count;A.hhe_root.after(A.log_delay_ms,A.decisions)
		except Empty:pass
		A.hhe_root.after(50,A.check_bot_decision_queue)
	def bot_decision(A,player):B=player;C=B[_p];D=[A[_p]for A in A.players if A.get(_p)is not _C and A[_p]is not C and A[_N]not in(_i,_T)];E=max(0,A.current_bet-B[_R]);F=A.get_community_cards();return C.decide(player_hand=B[_j][0],community_cards=F,opponents=D,pot=A.pot_size,to_call=E,balance=B[_H],street=A.street)
	def get_community_cards(A):
		if A.street==_A0:return[]
		if A.street==_AN:return list(A.flop[0])if A.flop else[]
		if A.street==_Ai:return list(A.flop[0]or[])+list(A.turn[0]or[])
		if A.street in(_Ah,_AO):return list(A.board[0])if A.board else[]
		return[]
	def execute_bot_decision(A,player,decision):
		G=decision;B=player;H=G[0];E=B[_Q]
		if H==_x:A.log_message(f"{E} folds.");A.modify_player(B,status=_i)
		elif H==_d:
			D=max(0,A.current_bet-B[_R])
			if D==0:A.log_message(f"{E} checks.");A.modify_player(B,status=_u)
			elif D>=B[_H]:F=B[_H];A.modify_player(B,change_balance=-F);A.modify_player(B,bet=B[_R]+F);A.pot_size+=F;A.log_message(f"{E} calls £{F} (ALL-IN).");A.modify_player(B,status=_u)
			else:A.modify_player(B,change_balance=-D);A.modify_player(B,bet=B[_R]+D);A.pot_size+=D;A.log_message(f"{E} calls £{D}.");A.modify_player(B,status=_u)
		elif H==_h:C=G[1]if len(G)>1 else A.current_bet*2;I=max(A.current_bet-B[_R]+A.big_blind_value,A.big_blind_value);C=max(C,I);C=min(C,B[_H]);A.modify_player(B,change_balance=-C);A.modify_player(B,bet=B[_R]+C);A.pot_size+=C;A.current_bet=B[_R];A.log_message(f"{E} raises to £{A.current_bet}.");A.modify_player(B,status=_u);A.reset_after_raise(except_player=B)
	def is_betting_complete(B):
		C=[A for A in B.players if A[_N]not in(_i,_T)]
		if len(C)<2:return _A
		for A in C:
			if A[_N]==_A1:return _B
			if A[_R]<B.current_bet and A[_H]>0:return _B
		return _A
	def reset_after_raise(A,except_player):
		C=except_player;D=C[_Aj]-1;A.action_position=(D+1)%A.player_count
		for B in A.players:
			if B is C:continue
			if B[_N]not in(_i,_T):B[_N]=_A1
	def bot_error(B,player,error):
		C=error;A=player
		try:messagebox.showerror('Bot Error',f"Error with {A[_Q]}:\n\n{C}\n\nBot will fold.")
		except Exception:print(f"Bot error ({A[_Q]}): {C}")
		B.log_message(f"{A[_Q]} encountered an error and has been folded.");B.modify_player(A,status=_T)
	def next_street(A):
		if A.current_street_index>=len(A.street_sequence):return
		A.street=A.street_sequence[A.current_street_index];A.current_street_index+=1
		if A.street==_A0:
			for B in A.players:
				if B[_N]not in(_i,_T,_u):B[_N]=_A1
			A.current_position=(A.initial_position+3)%A.player_count;A.action_position=A.current_position
		else:
			for B in A.players:
				if B[_N]not in(_i,_T):B[_N]=_A1
			A.current_bet=0
			for B in A.players:
				if B[_N]not in(_i,_T):B[_R]=0
			for D in range(A.player_count):
				C=(A.initial_position+1+D)%A.player_count
				if A.players[C][_N]!=_T:A.current_position=C;break
			A.action_position=A.current_position
		A.update_ui()
		if A.street==_AO:A.showdown()
		else:A.decisions()
	def advance_street(A):
		A.log_message(f"{A.street.capitalize()} betting complete.");B=[A for A in A.players if A[_N]not in(_i,_T)]
		if len(B)==1:
			C=B[0]
			if C[_S]:A.log_message(f"{C[_Q]} wins by default.");A.end_round(loss=_A)
			else:A.log_message('You win by default!');A.end_round(win=_A)
			return
		A.next_street()
	def showdown(A):
		K='hand_name';H='score';A.log_message(_C3,round_start=_A);A.update_ui();F=[A for A in A.players if A[_N]not in(_i,_T)]
		if not F:A.log_message('Error: no active players at showdown.');A.end_round(tie=_A);return
		if len(F)==1:D=F[0];A.log_message(f"{D[_Q]} wins (last remaining player).");A.end_round(loss=_A if D[_S]else _B,win=_B if D[_S]else _A);return
		E=[]
		for B in F:
			if not B[_j]or len(B[_j][0])<2:continue
			try:I=A.deck.evaluator.evaluate([A.deck.str_to_treys(B)for B in B[_j][0]],[A.deck.str_to_treys(B)for B in A.board[0]]);L=A.deck.evaluator.get_rank_class(I);J=A.deck.evaluator.class_to_string(L);E.append({_Q:B,H:I,K:J});A.log_message(f"{B[_Q]}:  {' '.join(B[_j][1])}  —  {J}")
			except Exception as M:A.log_message(f"Error evaluating {B[_Q]}'s hand: {M}")
		if not E:A.log_message('Error: could not evaluate any hands.');A.end_round(tie=_A);return
		E.sort(key=lambda x:x[H]);N=E[0][H];C=[A for A in E if A[H]==N];G=A.log_delay_ms*(len(A.log_queue)+2)
		if len(C)>1:
			O=', '.join(A[_Q][_Q]for A in C);P=any(not A[_Q][_S]for A in C);A.log_message(f"Split pot between {len(C)} players: {O}.")
			if P:A.hhe_root.after(G,lambda:A.end_round(win=_A,split_pot=_A,split_count=len(C)))
			else:A.hhe_root.after(G,lambda:A.end_round(loss=_A))
		else:
			D=C[0][_Q];A.log_message(f"{D[_Q]} wins with {C[0][K]}!")
			if D[_S]:A.hhe_root.after(G,lambda:A.end_round(loss=_A))
			else:A.hhe_root.after(G,lambda:A.end_round(win=_A))
	def update_user_poker_data(A):
		for C in A.players:
			if not C[_S]and C[_J]:
				D=_B;E=_B;F=_B;G=0
				for B in A.actions_logged:
					if B['street']==_A0:
						if B[_Ak]in(_d,_h):D=_A
						if B[_Ak]==_h:E=_A
					G+=B['bet_size']
					if B[_Ak]==_x:F=_A
				H=A.actions_logged[-1][_Ak]if A.actions_logged else _x;A.dbm.update_hand_statistics(user_id=C[_J],action=H,bet_size=G,pot_size=A.pot_size,voluntarily_entered=D,preflop_raised=E,faced_raise=F);A.dbm.resolve_player_actions(C[_J],A.current_round_number);break
	def end_round(A,*,win=_B,loss=_B,tie=_B,split_pot=_B,split_count=1):
		E=split_count;B=next((A for A in A.players if not A[_S]),_C)
		if not B:return
		if win:
			if split_pot and E>1:F=A.pot_size//E;B[_H]+=F;A.log_message(f"You split the pot and won £{F}!",is_win=_A)
			else:B[_H]+=A.pot_size;A.log_message(f"Congratulations! You won £{A.pot_size}!",is_win=_A)
		elif loss:A.log_message('You lost this round. Better luck next time.',is_loss=_A)
		elif tie:A.log_message("It's a tie!",tie=_A)
		A.dbm.modify_user_balance(A.user_data[_K],B[_H])
		if getattr(A,_BT,_C)and A.balance_label.winfo_exists():A.balance_label.config(text=f"Balance: £{B[_H]}")
		A.log_message(f"Your balance: £{B[_H]}.");A.update_user_poker_data();A.current_round_number+=1;A.actions_logged=[]
		if A.tournament_mode and A.tournament:
			G=A.tournament.evaluate_round_win(B,A.players);C=A.tournament.advance_round(G);A.log_message(C[_B6],is_tournament=_A)
			if C[_BP]:D=A.log_delay_ms*(len(A.log_queue)+2);A.hhe_root.after(D,lambda r=C:A.finish_tournament(r));return
			A.small_blind_value=A.tournament.current_small_blind;A.big_blind_value=A.tournament.current_big_blind
		D=A.log_delay_ms*(len(A.log_queue)+1);A.hhe_root.after(D,A.finish_end_round)
	def finish_tournament(B,result):A=result;C='Tournament Victory!'if A[_BQ]else'Tournament Over';messagebox.showinfo(C,A[_B6]);B.return_to_menu()
	def finish_end_round(A):
		A.current_bet=0
		if getattr(A,'current_bet_label',_C)and A.current_bet_label.winfo_exists():A.current_bet_label.config(text=_Ag)
		for B in A.players:
			if B[_S]and B[_H]<=0:B[_N]=_T;A.log_message(f"{B[_Q]} has been eliminated.")
		C=next((A for A in A.players if not A[_S]),_C)
		if C and C[_H]<=0:C[_N]=_T
		if A.check_game_over():return
		A.round_active=_B;A.round_number+=1
		if getattr(A,'start_button',_C)and A.start_button.winfo_exists():A.start_button.config(text=f"Start Round {A.round_number}")
		A.update_ui()
	def check_game_over(A):
		B=next((A for A in A.players if not A[_S]),_C)
		if B and B[_N]==_T:messagebox.showinfo('Game Over','Your chip balance has reached £0.  You will be returned to the main menu.');A.return_to_menu();return _A
		C=[A for A in A.players if A[_S]and A[_N]!=_T]
		if len(C)==0:messagebox.showinfo('Victory!','Congratulations! You have eliminated all opponents and won the game!');A.return_to_menu();return _A
		return _B
	def return_to_menu(A,is_error=_B,error=_C):
		if is_error:messagebox.showerror(_L,f"{error}\n\nExiting game.")
		A.hhe_root.destroy();Casino_Interface(administrator=_A if A.user_data.get(_Z)else _B,user_data=A.user_data)
	def fold(A):
		for B in A.players:
			if not B[_S]:A.log_message(f"{B[_Q]} folds.");A.modify_player(B,status=_i);A.player_turn=_B;A.log_player_action_to_db(_x,0);A.current_position=(A.current_position+1)%A.player_count;A.update_ui();A.decisions();break
	def call(A):
		for B in A.players:
			if not B[_S]:
				C=max(0,A.current_bet-B[_R])
				if C==0:A.log_message(f"{B[_Q]} checks.");E,F='check',0
				elif C>=B[_H]:D=B[_H];A.modify_player(B,change_balance=-D);A.modify_player(B,bet=B[_R]+D);A.pot_size+=D;A.log_message(f"{B[_Q]} calls £{D} (ALL-IN).");E,F=_d,D
				else:A.modify_player(B,change_balance=-C);A.modify_player(B,bet=B[_R]+C);A.pot_size+=C;A.log_message(f"{B[_Q]} calls £{C}.");E,F=_d,C
				A.modify_player(B,status=_u);A.player_turn=_B;A.log_player_action_to_db(E,F);A.current_position=(A.current_position+1)%A.player_count;A.update_ui();A.decisions();break
	def raise_bet(A):
		E='Invalid Raise'
		try:C=int(A.bet_var.get())
		except ValueError:messagebox.showerror(E,'Please enter a valid number.');return
		for B in A.players:
			if not B[_S]:
				D=max(A.current_bet-B[_R]+A.big_blind_value,A.big_blind_value)
				if C<D:messagebox.showerror(E,f"The minimum raise is £{D}.");return
				if C>B[_H]:messagebox.showerror('Insufficient Funds','You do not have enough chips to raise by that amount.');return
				A.modify_player(B,change_balance=-C);A.modify_player(B,bet=B[_R]+C);A.pot_size+=C;A.current_bet=B[_R];A.log_message(f"{B[_Q]} raises to £{A.current_bet}.");A.modify_player(B,status=_u);A.log_player_action_to_db(_h,C);A.reset_after_raise(except_player=B);A.current_position=(A.current_position+1)%A.player_count;A.player_turn=_B;A.update_ui();A.decisions();break
if __name__=='__main__':
	if'--admin'in sys.argv:Admin_Interface()
	else:User_Interface()