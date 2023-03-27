<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Logout</title>
    <script type="text/javascript" src="https://ajax.googleapis.com/ajax/libs/jquery/1.8.3/jquery.min.js"></script>
</head>
<body>
    <?php 
    
   session_start();
   session_unset();
    session_destroy();
  echo '<script> window.location="http://localhost/major%20project/index.php"; </script>';
 
    ?>
  

     
</body>
</html>
