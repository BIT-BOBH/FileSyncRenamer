import shutil
import time
import colorama
import json
import os
from os import path, stat
import hidden
import hashlib

VERSION = "1.0.0"
AUTHOR = "BobH"

g_directory_files = [] # 存储所有遍历到的文件信息
g_hash_map = {} # hash对应文件名
g_file_synced = {} # hash对应是否被同步过了,用于检查哪些文件因为缺失而没被同步
ignored_items = []

def PrintInfo():
    print(colorama.Fore.YELLOW + "[ FileSyncRenamer @ " + VERSION + " ]")
    print(colorama.Fore.RESET + "作者: " + colorama.Fore.RED + AUTHOR)

def InputAction():
    print(colorama.Fore.RESET + "目前脚本支持一下两种操作:")
    print(colorama.Fore.RESET + "1. " + colorama.Fore.GREEN + "保存 " + colorama.Fore.CYAN + "(将当前目录结构和每一个文件名保存为一个json文件便于传输)")
    print(colorama.Fore.RESET + "2. " + colorama.Fore.GREEN + "读取 " + colorama.Fore.CYAN + "(读取保存的json文件并还原目录结构和文件名)")
    inputAction = input(colorama.Fore.RESET + "请输入你的操作(数字1或2): ")
    while not inputAction.isdigit():
        inputAction = input("请输入你的操作(数字1或2): ")
    return int(inputAction)

pushFileCnt = 0

def PushFileInfo(relativeFilePath):
    global pushFileCnt,g_directory_files,ignored_items
    # 忽略的文件不push进去
    if ignored_items.count(relativeFilePath) > 0:
        return
    # print(colorama.Fore.GREEN + relativeFilePath)
    pushFileCnt = pushFileCnt + 1
    fileObj = {}
    fileObj['fileName'] = relativeFilePath
    g_directory_files.append(fileObj)

def CalcFileHash(relativeFilePath):
    with open(relativeFilePath, 'rb') as fp:
        data = fp.read()
        return hashlib.sha256(data).hexdigest()
    return ""

def UpdateProgress(percent):
    i = int(60 * percent)
    finsh = "▓" * i
    need_do = "-" * (60 - i)
    progress = percent * 100
    print("\r{:^3.0f}%[{}->{}]".format(progress, finsh, need_do), end="")

def CalcAllFileHash():
    global g_directory_files,pushFileCnt
    for i in range(0,pushFileCnt):
        UpdateProgress((i+1) / pushFileCnt)
        curItem = g_directory_files[i]
        curItem['sha256'] = CalcFileHash(curItem['fileName'])
    print("")


def EnumDirectory(relativeDirPath):
    global ignored_items
    if ignored_items.count(relativeDirPath) > 0:
        return
    dirItems = os.listdir(relativeDirPath)
    for item in dirItems:
        itemRelativePath = relativeDirPath + item
        if path.isfile(itemRelativePath):
            # 是文件我们保存文件信息
            # 判断文件如果被隐藏则忽略
            if not hidden.is_hidden(itemRelativePath):
                PushFileInfo(itemRelativePath)
        elif path.isdir(itemRelativePath):
            nxtDir = itemRelativePath + path.sep
            EnumDirectory(nxtDir)
        else:
            print(colorama.Fore.RED + "未知文件项: " + itemRelativePath)

def ReadIgnoreItems():
    global ignored_items
    if not path.exists("./ignore.list"):
        print(colorama.Fore.YELLOW + "没有在根目录找到忽略文件列表 ignore.list, 可能会保存一些无关文件!")
    else:
        ignoreFile = open("./ignore.list")
        while True:
            line = ignoreFile.readline()
            if not line: break
            if line == "\n": continue
            if line == "": continue
            if line[0] == '#': continue
            line = line.replace('/', path.sep)
            if(line[-1] == '\n'): line = line[0:-1]
            ignored_items.append(line)

def SaveDirectory():
    ReadIgnoreItems()
    print(colorama.Fore.BLUE + "共读取到忽略项:" + str(len(ignored_items)) + " 个!")
    saveFileName = input(colorama.Fore.RESET + "请输入保存文件名(默认latest.fs.json): ")
    if saveFileName == "": saveFileName = "latest.fs.json"
    EnumDirectory("." + path.sep)
    CalcAllFileHash()
    with open(saveFileName, "w") as saveFile:
        saveFile.write(json.dumps(g_directory_files))
        print(colorama.Fore.GREEN + "写出信息至{0}成功!".format(saveFileName))

def ReadJsonData(jsonFile):
    global g_directory_files
    try:
        jFile = open(jsonFile,"r")
        jsonContent = jFile.read()
        g_directory_files = json.loads(jsonContent)
    except Exception as e:
        print(colorama.Fore.RED + "读取json文件出错!")
        raise Exception("读取json文件出错")

def MoveFile(srcFile, dstFile):
    dstPath,dstName = path.split(dstFile)
    if not path.exists(dstPath):
        os.makedirs(dstPath)
    shutil.move(srcFile, dstFile)

fileSynced = 0

def TrySyncFile(relativeFilePath):
    global fileSynced
    fHash = CalcFileHash(relativeFilePath)
    if fHash not in g_hash_map:
        return
    MoveFile(relativeFilePath, g_hash_map[fHash])
    fileSynced = fileSynced + 1
    g_file_synced[fHash] = True
    

def EnumDirectory1(relativeDirPath):
    dirItems = os.listdir(relativeDirPath)
    for item in dirItems:
        itemRelativePath = relativeDirPath + item
        if path.isfile(itemRelativePath):
            # 是文件则查表看是否存在
            TrySyncFile(itemRelativePath)
            UpdateProgress(fileSynced / len(g_directory_files))
        elif path.isdir(itemRelativePath):
            nxtDir = itemRelativePath + path.sep
            EnumDirectory1(nxtDir)
        else:
            print(colorama.Fore.RED + "未知文件项: " + itemRelativePath)

def SyncAllFiles():
    EnumDirectory1("." + path.sep)
    print("")
    # 检查遗漏文件项
    for sha256,fileName in g_hash_map.items():
        if sha256 not in g_file_synced:
            print(colorama.Fore.YELLOW + "未同步的文件名: {0}, sha256 = {1}".format(fileName, sha256))
    print(colorama.Fore.GREEN + "✅ 同步完毕")
    print(colorama.Fore.CYAN + "⬆️ 如果输出了未同步的文件,可能因为你缺失一些文件,请和伙伴联系补充")

def LoadDirectory():
    loadFileName = input(colorama.Fore.RESET + "请输入载入文件名(默认latest.fs.json): ")
    if loadFileName == "": loadFileName = "latest.fs.json"
    ReadJsonData(loadFileName)
    for fileInfo in g_directory_files:
        g_hash_map[fileInfo['sha256']] = fileInfo['fileName']
    print(colorama.Fore.BLUE + "读取到 {0} 个文件信息，开始同步...".format(len(g_directory_files)))
    SyncAllFiles()

if __name__ == '__main__':
    PrintInfo()
    action = InputAction()
    if action == 1:
        # 保存
        SaveDirectory()
    elif action == 2:
        # 读取
        LoadDirectory()
    else:
        print(colorama.Fore.RED + "错误的输入!")