<?php
include "process1.php";
session_start();

$_SESSION['nobackadmin']=1;
$_SESSION['noback']=1;

if(isset($_SESSION['active']))
{
  echo '<script>  window.location="http://localhost/major%20project/user module/individual.php"; </script>';
}
else if(isset($_SESSION['activeadmin']))
{
  echo '<script>  window.location="http://localhost/major%20project/admin module/admin.php"; </script>';
}

error_reporting(0);


?>




<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Login</title>
  <style>
  <?php include 'css/style.css'; ?>
    body{
      background-image: url("images/garb2.jpg");
      background-size: cover;
    }

  
  </style>
</head>
<body>

<?php

function test_input($data)
{
  $data=trim($data);
  $data=stripslashes($data);
  $data=htmlspecialchars($data);
  return $data;
}
if(isset($_POST['login']))
{
  $email=test_input($_POST["email"]);
  $pass=test_input($_POST['pass']);

  $sql="SELECT `Password`  FROM `member` WHERE `Email`='$email'";
  $sql2="SELECT `Password` FROM `admin` WHERE `Email`='$email'";
  $query=mysqli_query($conn,$sql);
  $query2=mysqli_query($conn,$sql2);
  $row=mysqli_fetch_assoc($query);
  $row2=mysqli_fetch_assoc($query2);
  
  if($query AND $row['Password']==$pass)
  {
    $_SESSION["email"]=$email;
    $_SESSION["pass"]=$pass;
    echo '<script> alert("Login successfull !");
          window.location="http://localhost/major%20project/user module/individual.php"; </script>';
        


  }

else if($query2 AND $row2['Password']==$pass)
{

  $_SESSION["email"]=$email;
  $_SESSION["pass"]=$pass;
  echo '<script> alert("Login successfull !");
        window.location="http://localhost/major%20project/admin module/admin.php"; </script>';
    
}

  else{
    echo '<script>alert("Couldnt login! Please signup before login");</script>';
    
  }

  


}

?>
  <section id="navbar">
    <div class="container header">

     <nav>
       <div class="logo">
           <img src="images/grlogo2.svg" alt="logo">
 
  
        </div>
      
      <ul id="navmenu">
          <li><a href="http://localhost/major%20project/index.php">Home</a> </li>
          <li><a href="http://localhost/major%20project/aboutus.php">About Us</a> </li>
          <li><a href="http://localhost/major%20project/privacypolicy.php">Privacy Policy</a>  </li>
          <li> <a href="http://localhost/major%20project/contact.php"> Contact Us</a> </li>
          <li> <a id="btn" href="http://localhost/major%20project/login.php"> Login/SignUp</a></li>
  
          
      </ul>



     </nav>        
   


    </div>



   </section>

   <section id="loginpage">

    <div class="container">
         
       <div class="details">
       <div class="front">
        <form method="POST" action="<?php echo htmlspecialchars($_SERVER["PHP_SELF"]) ?>">
          <h1>Login</h1>
          <label for="emailaddress">Email address:</label>
          <input type="email" name="email" required>
          <label for="Password">Password:</label>
          <input type="password" name="pass" required>
         <center> <input type="submit" name="login" value="Login"></center>
      <span> Don't have an account ? <a href="http://localhost/major%20project/signup2.php" > Sign Up </a></span>
         </form>


       </div>
       
    
        <div class="back">




        </div>



  
       


       </div>



    </div>



    </section>






   
    <section id="footer" class="footer">
        <div class="heading2">
         <h2> QuickLinks</h2>
        </div> 
         
         
         <div class="container">
           
            <div class="quicklinks">
   
                <ul>
   
                 <li><a href="http://localhost/major%20project/aboutus.php"> About Us</a></li>
                </ul>
   
                <ul>
                   <li> <a href="http://localhost/major%20project/contact.php"> Contact Us</a> </li>
       
                </ul>
   
   
                <ul>
   
                 <li><a href="http://localhost/major%20project/privacypolicy.php"> Privacy Policy</a></li>
                </ul>
   
   
                <ul>
   
                 <li><a href="sale/wanttobuy.php"> Want to Buy?</a></li>
                </ul>
   
   
                </div>
            </div>
   
        
   
     <div class="footlogo">
   
   <img src="images/grlogo2.svg" alt="logo">
     </div>
       </section>
   
    
</body>
</html>