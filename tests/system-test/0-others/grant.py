from ssl import ALERT_DESCRIPTION_CERTIFICATE_UNOBTAINABLE
import taos
import sys
import time
import os

from util.log import *
from util.sql import *
from util.cases import *
from util.dnodes import *
from util.dnodes import TDDnodes
from util.dnodes import TDDnode
import time
import socket
import subprocess

class MyDnodes(TDDnodes):
    def __init__(self ,dnodes_lists):
        super(MyDnodes,self).__init__()
        self.dnodes = dnodes_lists  # dnode must be TDDnode instance
        if platform.system().lower() == 'windows':
            self.simDeployed = True
        else:
            self.simDeployed = False

class TDTestCase:
    noConn = True
    def getTDinternalPath():
        path_parts = os.getcwd().split(os.sep)
        try:
            tdinternal_index = path_parts.index("TDinternal")
        except ValueError:
            raise ValueError("The specified directory 'TDinternal' was not found in the path.")
        return os.sep.join(path_parts[:tdinternal_index + 1])
        
    def init(self, conn, logSql, replicaVar=1):
        tdLog.debug(f"start to excute {__file__}")
        self.TDDnodes = None
        self.depoly_cluster(5)
        self.master_dnode = self.TDDnodes.dnodes[0]
        self.host=self.master_dnode.cfgDict["fqdn"]
        conn1 = taos.connect(self.master_dnode.cfgDict["fqdn"] , config=self.master_dnode.cfgDir)
        tdSql.init(conn1.cursor(), True)
        self.TDinternal = TDTestCase.getTDinternalPath()
        self.workPath = os.path.join(self.TDinternal, "debug", "build", "bin")
        tdLog.info(self.workPath)

    def getBuildPath(self):
        selfPath = os.path.dirname(os.path.realpath(__file__))

        if ("community" in selfPath):
            projPath = selfPath[:selfPath.find("community")]
        else:
            projPath = selfPath[:selfPath.find("tests")]

        for root, dirs, files in os.walk(projPath):
            if ("taosd" in files or "taosd.exe" in files):
                rootRealPath = os.path.dirname(os.path.realpath(root))
                if ("packaging" not in rootRealPath):
                    buildPath = root[:len(root) - len("/build/bin")]
                    break
        return buildPath

    def depoly_cluster(self ,dnodes_nums):

        testCluster = False
        valgrind = 0
        hostname = socket.gethostname()
        dnodes = []
        start_port = 6030
        for num in range(1, dnodes_nums+1):
            dnode = TDDnode(num)
            dnode.addExtraCfg("firstEp", f"{hostname}:{start_port}")
            dnode.addExtraCfg("fqdn", f"{hostname}")
            dnode.addExtraCfg("serverPort", f"{start_port + (num-1)*100}")
            dnode.addExtraCfg("monitorFqdn", hostname)
            dnode.addExtraCfg("monitorPort", 7043)
            dnodes.append(dnode)

        self.TDDnodes = MyDnodes(dnodes)
        self.TDDnodes.init("")
        self.TDDnodes.setTestCluster(testCluster)
        self.TDDnodes.setValgrind(valgrind)

        self.TDDnodes.setAsan(tdDnodes.getAsan())
        self.TDDnodes.stopAll()
        for dnode in self.TDDnodes.dnodes:
            self.TDDnodes.deploy(dnode.index,{})

        for dnode in self.TDDnodes.dnodes:
            self.TDDnodes.starttaosd(dnode.index)

        # create cluster
        for dnode in self.TDDnodes.dnodes[1:]:
            # print(dnode.cfgDict)
            dnode_id = dnode.cfgDict["fqdn"] +  ":" +dnode.cfgDict["serverPort"]
            dnode_first_host = dnode.cfgDict["firstEp"].split(":")[0]
            dnode_first_port = dnode.cfgDict["firstEp"].split(":")[-1]
            cmd = f"{self.getBuildPath()}/build/bin/taos -h {dnode_first_host} -P {dnode_first_port} -s \"create dnode \\\"{dnode_id}\\\"\""
            print(cmd)
            os.system(cmd)

        time.sleep(2)
        tdLog.info(" create cluster done! ")

    def s0_five_dnode_one_mnode(self):
        tdSql.query("select * from information_schema.ins_dnodes;")
        tdSql.checkData(0,1,'%s:6030'%self.host)
        tdSql.checkData(4,1,'%s:6430'%self.host)
        tdSql.checkData(0,4,'ready')
        tdSql.checkData(4,4,'ready')
        tdSql.query("select * from information_schema.ins_mnodes;")
        tdSql.checkData(0,1,'%s:6030'%self.host)
        tdSql.checkData(0,2,'leader')
        tdSql.checkData(0,3,'ready')
        tdSql.error("create mnode on dnode 1;")
        tdSql.error("drop mnode on dnode 1;")
        tdSql.execute("create database if not exists audit");
        tdSql.execute("use audit");
        tdSql.execute("create table operations(ts timestamp, c0 int primary key,c1 bigint,c2 int,c3 float,c4 double) tags(t0 bigint unsigned)");
        tdSql.execute("create table t_operations_abc using operations tags(1)");
        tdSql.execute("drop database if exists db")
        tdSql.execute("create database if not exists db replica 1")
        tdSql.execute("use db")
        tdSql.execute("create table stb0(ts timestamp, c0 int primary key,c1 bigint,c2 int,c3 float,c4 double) tags(t0 bigint unsigned)");
        tdSql.execute("create table ctb0 using stb0 tags(0)");
        tdSql.execute("create stream streams1 trigger at_once IGNORE EXPIRED 0 IGNORE UPDATE 0  into streamt as select _wstart, count(*) c1, count(c2) c2 , sum(c3) c3 , max(c4) c4 from stb0 interval(10s)");
        tdSql.execute("create topic topic_stb_column as select ts, c3 from stb0");
        tdSql.execute("create topic topic_stb_all as select ts, c1, c2, c3 from stb0");
        tdSql.execute("create topic topic_stb_function as select ts, abs(c1), sin(c2) from stb0");
        tdSql.execute("create view view1 as select * from stb0");
        
    def getConnection(self, dnode):
        host = dnode.cfgDict["fqdn"]
        port = dnode.cfgDict["serverPort"]
        config_dir = dnode.cfgDir
        return taos.connect(host=host, port=int(port), config=config_dir)

    def s1_check_alive(self):
        # check cluster alive
        tdLog.printNoPrefix("======== test cluster alive: ")
        tdSql.checkDataLoop(0, 0, 1, "show cluster alive;", 20, 0.5)

        tdSql.query("show db.alive;")
        tdSql.checkData(0, 0, 1)

    def s2_check_show_grants_ungranted(self):
        tdLog.printNoPrefix("======== test show grants ungranted: ")
        self.infoPath = os.path.join(self.workPath, ".clusterInfo")
        infoFile = open(self.infoPath, "w")
        try:
            tdSql.query(f'select create_time,expire_time,version from information_schema.ins_cluster;')
            tdSql.checkEqual(len(tdSql.queryResult), 1)
            infoFile.write(";".join(map(str, tdSql.queryResult[0])) + "\n")
            tdSql.query(f'show cluster machines;')
            tdSql.checkEqual(len(tdSql.queryResult), 1)
            infoFile.write(";".join(map(str,tdSql.queryResult[0])) + "\n")
            tdSql.query(f'show grants;')
            tdSql.checkEqual(len(tdSql.queryResult), 1)
            infoFile.write(";".join(map(str,tdSql.queryResult[0])) + "\n")
            tdSql.query(f'show grants full;')
            tdSql.checkEqual(len(tdSql.queryResult), 31)
            
            if infoFile:
                infoFile.flush()

            files_and_dirs = os.listdir(f'{self.workPath}')
            print(f"files_and_dirs: {files_and_dirs}")

            process = subprocess.Popen(f'{self.workPath}{os.sep}grantTest', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = process.communicate() 
            output = output.decode(encoding="utf-8")
            error = error.decode(encoding="utf-8")
            print(f"code: {process.returncode}")
            print(f"error:\n{error}")
            tdSql.checkEqual(process.returncode, 0)
            tdSql.checkEqual(error, "")
            lines = output.splitlines()
            for line in lines:
                if line.startswith("code:"):
                    fields  = line.split(":")
                    tdSql.error(f"{fields[2]}", int(fields[1]), fields[3])
        except Exception as e:
            if os.path.exists(self.infoPath):
                os.remove(self.infoPath)
            raise Exception(repr(e))
        finally:
            if infoFile:
                infoFile.close()

    def s3_check_show_grants_granted(self):
        tdLog.printNoPrefix("======== test show grants granted: ")
        try:
            process = subprocess.Popen(f'{self.workPath}{os.sep}grantTest 1', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = process.communicate()
            output = output.decode(encoding="utf-8")
            error = error.decode(encoding="utf-8")
            print(f"code: {process.returncode}")
            print(f"error:\n{error}")
            print(f"output:\n{output}")
            tdSql.checkEqual(process.returncode, 0)
        except Exception as e:
            raise Exception(repr(e))
        finally:
            if os.path.exists(self.infoPath):
                os.remove(self.infoPath)

    def run(self):
        # print(self.master_dnode.cfgDict)
        # keep the order of following steps
        self.s0_five_dnode_one_mnode()
        self.s1_check_alive()
        self.s2_check_show_grants_ungranted()
        self.s3_check_show_grants_granted() 


    def stop(self):
        tdSql.close()
        tdLog.success(f"{__file__} successfully executed")

tdCases.addLinux(__file__, TDTestCase())
tdCases.addWindows(__file__, TDTestCase())