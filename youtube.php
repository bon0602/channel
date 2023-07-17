<?php
/**
youtube LIVE: https://www.youtube.com/watch?v=lu_BJKxqGnk
==> ?v=lu_BJKxqGnk &hd=0-7
==> http://127.0.0.1/youtube.php?v=lu_BJKxqGnk&hd=5
**/

$v = $_GET['v'];
$hd = $_GET['hd'];
$data = file_get_contents('https://www.youtube.com/watch?v='.$v);
preg_match('/"hlsManifestUrl":"(.*?)"/', $data, $matches);
$data = file_get_contents($matches[1]);
$ext = explode("\n", $data);
unset($ext[0]);
$ext = array_map('trim', $ext);
$ext = array_chunk($ext, 2);
header("Location:". $ext[$hd][0]);

?>