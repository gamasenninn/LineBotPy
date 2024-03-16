import IPython
from io import StringIO
import sys

def execute_gpt_code(code):
    """
    GPTから生成されたコードをIPython環境で実行し、結果とExecutionResultを返す関数。
    """
    # IPythonのインタラクティブシェルインスタンスを作成
    ipython_shell = IPython.get_ipython()

    if ipython_shell is None:
        # IPythonのインタラクティブシェルが存在しない場合、新たに作成
        ipython_shell = IPython.core.interactiveshell.InteractiveShell()

    # 標準出力をキャプチャする
    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()

    # コードを実行
    result = ipython_shell.run_cell(code)

    # 標準出力を元に戻す
    sys.stdout = old_stdout

    # 実行結果を取得
    execution_output = mystdout.getvalue()

    return execution_output, result

# Run application
if __name__ == "__main__":
    # GPTから生成されたコードの例
    gpt_generated_code = """
    def hello_world():
        print("Hello, world!")

    hello_world()
    """

    # コードを実行し、結果を表示
    execution_output, execution_result = execute_gpt_code(gpt_generated_code)

    print("出力結果:")
    print(execution_output)
    print("\n実行結果の情報:")
    print(execution_result)

