#coding: utf-8

import os, pygit2, sys, zipfile, glob;
from subprocess import Popen, PIPE, STDOUT;
import urllib2

subprocess_env = dict(os.environ);
subprocess_env['LC_ALL'] = "en_US.UTF-8";

def execute(executable, *args, **kwargs):
    ret_pipe = kwargs.pop('ret_pipe', False);
    cwd = kwargs.pop("cwd", None);
    if kwargs.pop('stderr', False):
	stderr = STDOUT;
    else:
	stderr = PIPE
    process = Popen(args=(executable,) + args, shell=False, stdout=PIPE, stderr=stderr,stdin=PIPE,cwd=cwd,env=subprocess_env);
    if ret_pipe:
	return process.stdout;
    process.stdin.close();
    output = process.stdout.read();
    process.wait();
    if stderr == STDOUT:
	errors = output;
    else:
	errors = process.stderr.read();
    if process.returncode != 0:
	sys.stdout.flush();
	return errors, process.returncode;
    return output, 0;

git_path = execute('which', 'git')

if git_path and git_path[1] == 0:
    git_path = git_path[0][:-1]
    print "当前git路径", git_path
else:
    sys.exit("git 路径没有找到")

def git(*args, **kwargs):
    return execute(git_path, "--no-pager", *args, **kwargs);

class Pack:
    tags = []
    submodules = [];
    last_version = 0;
    #过滤全局的
    ingore_files = ['.git', '.gitignore', '.gitmodules', '.DS_Store']
    #特别路径过滤
    spec_ingore_files = []

    #sql_url = "http://cdn.img.dbplay.com/update/sql-cmdp_cms.txt"

    def __init__(self, path=os.getcwd()):
	main_dir = os.path.join(path, "zqcms");
	self.cms_path = path;
	self.main_dir = main_dir;
	self.dist_dir = os.path.join(path, "python");
	data_dir = os.path.join(main_dir, "data");
	self.repo = pygit2.Repository(main_dir);

	self.get_tags();
	self.get_submodules();
	
	#download the last sql
	#self.get_last_sql();

	self.update_version();
	self.get_diff_files_list();
	self.package_last_version();

    def get_last_sql(self):
	print "=== start download the last database sql";
	file_name = self.sql_url.split("/")[-1];
	u = urllib2.urlopen(self.sql_url);
	f = os.path.join(self.main_dir, "install", file_name);
	f = open(f, "wb");
	meta = u.info();
	file_size = int(meta.getheaders("Content-Length")[0])

	print "=== Downloading: %s Bytes: %s" % (file_name, file_size)

	file_size_dl = 0
	block_sz = 8192
	while True:
	    buffer = u.read(block_sz)
	    if not buffer:
		break

	    file_size_dl += len(buffer)
	    f.write(buffer)
	    status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
	    status = status + chr(8)*(len(status)+1)
	    print status,

	f.close()

    def update_version(self):
	last = self.tags[0]
	self.last_version = last.name;

	print "=== The last version: %s" % self.last_version;

	ver_txt = os.path.join(self.main_dir, "caches", "update", 'ver.txt');
	txt = open(ver_txt, mode='w');
	txt.write(self.last_version);
	txt.close();

	self.ver_txt = ver_txt[len(self.main_dir)+1:];
    
    def get_submodule_diff_files_list(self, submodule_dir, submodule, git_str):
	diff_info = git_str[0].strip().split();
	#find -Subproject
	pre_subproject_position = diff_info.index('-Subproject')
	pre_subproject_version_position = pre_subproject_position + 2; #手动偏移2位
	pre_version_hash = diff_info[pre_subproject_version_position];
	#find +Subproject
	last_subproject_position = diff_info.index('+Subproject');
	last_subproject_version_position = last_subproject_position + 2;
	last_version_hash = diff_info[last_subproject_version_position];
	
	update_list = []

	if (pre_version_hash and last_version_hash):
	    tfiles = git("diff", pre_version_hash, last_version_hash, "--diff-filter=A,C,M,T", "--name-only", cwd=submodule_dir)[0];
	    tfiles = tfiles.strip().split();
	    update_list = [os.path.join(submodule,f) for f in tfiles];
	else:
	    update_list.append(submodule)
	
	return update_list;

    def get_diff_files_list(self):
	last = self.tags[0]
	self.last_version = last.name;
	
	#get diff
	pervious = self.tags[1]
    
	last_target = self.repo[last.target];
	pervious_target = self.repo[pervious.target];
	
	"""
	git-diff diff-filter=[A|C|D|M|R|T|U|X|B]
	Select only files that are Added (A), Copied (C), Deleted (D), Modified (M), Renamed (R), have their type (i.e. regular
           file, symlink, submodule, ...) changed (T), are Unmerged (U), are Unknown (X), or have had their pairing Broken (B). Any
           combination of the filter characters (including none) can be used. When * (All-or-none) is added to the combination, all
           paths are selected if there is any file that matches other criteria in the comparison; if there is no file that matches
           other criteria, nothing is selected.
	"""
	tfiles = git("diff", pervious_target.hex, last_target.hex, "--diff-filter=A,C,M,T", "--name-only", cwd=self.main_dir)[0];
	tfiles = tfiles.strip().split();

	files = list();
	if len(tfiles):
	    for f in tfiles:
		if (f in self.submodules):
		    #检查模块的差异
		    submodule_dir = os.path.join(self.main_dir, f);
		    submodule_update_list = self.get_submodule_diff_files_list(submodule_dir, f, git("diff", pervious_target.hex, last_target.hex, f, cwd=self.main_dir));

		    if len(submodule_update_list):
			#merge
			files = files + submodule_update_list;
		else:
		    files.append(f)
	    self.package_patch(files);

    def get_tags(self):
	print "=== Parsing package version";
	data = self.repo.listall_references();
	
	for item in data:
	    ref = self.repo.lookup_reference(item);
	    '''
	    ref is commit type
	    '''
	    if (ref.type == pygit2.GIT_OBJ_COMMIT):
		'''
		get ref oid
		'''
		oid = ref.oid;
		ref_obj = self.repo[oid];
		#it's tag, has push to the server
		if isinstance(ref_obj, pygit2.Tag):
		    self.tags.append(ref_obj);
	    else:
		continue;
	
	#sort by tagger time
	self.tags.sort(lambda x,y: cmp(y.tagger.time, x.tagger.time));

    def get_submodules(self):
	print "=== Get package submodules"
	dot_git_dir = self.repo.path;
	modules_dir = os.path.join(dot_git_dir, "modules");

	if os.path.isdir(modules_dir) and os.path.exists(modules_dir):
	    modules = glob.glob(modules_dir+"/*");
	    if len(modules):
		self.submodules = [ x[len(modules_dir) + 1:] for x in modules ]

    #遍历所有文件夹中的文件, 并列出来
    def _get_files(self, files, is_dir = False):
	if is_dir:
	    base = files;
	    for root, dirs, files in os.walk(base):
		for f in files:
		    #文件绝对路径
		    file_path = os.path.join(root, f);
		    #相对路径
		    rel_path = file_path[len(self.main_dir) + 1:]
		    #带有cmdp_cms的绝对文件路径
		    ab_path = file_path[len(self.cms_path) + 1:]
		    if ((f not in self.ingore_files) and (root.find(".git") == -1) and (ab_path not in self.spec_ingore_files)):
		        self.files.append(rel_path);
	else:
	    for f in files:
		file_path = os.path.join(self.main_dir, f);#文件相对路径
		ab_path = os.path.join(self.main_dir[len(self.cms_path) + 1:], f);
		if os.path.isdir(file_path):
		    self._get_files(file_path, True);
		elif os.path.isfile(file_path) and f not in self.ingore_files and (ab_path not in self.spec_ingore_files):
		    self.files.append(file_path[len(self.main_dir)+1:]);

    '''
    打包差异包补丁
    '''
    def package_patch(self, files):
	print "=== package patch zip";
	self.files = [];
	self._get_files(files);
	self.files.append(self.ver_txt);
	
	filelist = open(os.path.join(self.dist_dir, "%s.file.txt") % self.last_version, mode='w');
	for f in self.files:
	    filelist.write(f+"\n");

    '''
    打包最新版本
    '''
    def package_last_version(self):
	print "=== package install zip";
	git('checkout', self.last_version, cwd=self.main_dir);
	self.files = [];
	self._get_files(self.main_dir, True);
	self.files.append(self.ver_txt);

	zip_file = zipfile.ZipFile(os.path.join(self.dist_dir, "zqcms-%s.zip") % self.last_version, mode='w', compression=zipfile.ZIP_DEFLATED);

	for f in self.files:
	    file_path = os.path.join(self.main_dir, f);
	    rel_path = os.path.join("uploads", f);
	    zip_file.write(file_path, rel_path);

	zip_file.close();
	git('checkout', 'master', cwd=self.main_dir);

if __name__ == '__main__':
    package = Pack();
