function copy(sourceId, targetName) {
  var sourceRoot = DriveApp.getFolderById(sourceId);
  var targetRoot = DriveApp.getFoldersByName(targetName);
  targetRoot = targetRoot.hasNext() ? targetRoot.next() : DriveApp.createFolder(targetName);
  copyFolder(sourceRoot, targetRoot);
}

function copyFolder(source, target) {
  var subSources = source.getFolders();
  while (subSources.hasNext()) {
    var subSource = subSources.next();
    var subTarget = target.getFoldersByName(subSource.getName());
    subTarget = subTarget.hasNext() ? subTarget.next() : target.createFolder(subSource.getName());
    copyFolder(subSource, subTarget);
  }
  var sourceFiles = source.getFiles();
  while (sourceFiles.hasNext()) {
    var sourceFile = sourceFiles.next();
    if (!target.getFilesByName(sourceFile.getName()).hasNext()) {
      try {
        sourceFile.makeCopy(sourceFile.getName(), target);
      } catch (e) {
        Logger.log("Could not copy " + sourceFile.getName());
      }
    }
  }
}

function run() {
  copy("123435234659823645298347652398744", "Copy of Big Move");
}
