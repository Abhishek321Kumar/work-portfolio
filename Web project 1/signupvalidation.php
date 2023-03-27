<?php

session_start();



$fnamerr=$lnamerr=$emailerr=$phnoerr=$adderr=$spasserr=$cpasserr=$stateerr="";
$fname=$lname=$email=$phno=$address=$spass=$cpass=$state="";
$flag=0;






function test_input($data)
{
  $data=trim($data);
  $data=stripslashes($data);
  $data=htmlspecialchars($data);
  return $data;
}

if($_SERVER["REQUEST_METHOD"]=="POST")
{
  if(empty($_POST["ftname"])){
    $fnamerr="First name is mandatory";
    $flag=1;

  }
  else{
    $fname=test_input($_POST["ftname"]);


    if(!preg_match("/^[a-zA-Z-']*$/",$fname))
    {
      $fnamerr="Enter valid name";
      $flag=1;
    }
    else{
      $_SESSION['fname']=$fname;
    }
  }


  if(empty($_POST["ltname"])){
    $lnamerr="Last name is mandatory";
    $flag=1;
   

  }
  else{

    $lname=test_input($_POST["ltname"]);

    if(!preg_match("/^[a-zA-Z-']*$/",$lname))
    {
      $lnamerr="Enter valid name";
      $flag=1;
    }
    else{
      $_SESSION['lname']=$lname;
    }
   
  }

  if(empty($_POST["email"])){
    $emailerr="Email is mandatory";
    $flag=1;

  }
  else{

    $email=strtolower(test_input($_POST["email"]));
    if(!filter_var($email,FILTER_VALIDATE_EMAIL)){
      $emailerr="Invalid email format";
      $flag=1;
    
    }
    
   
  }


  if(empty($_POST["address"])){
    $adderr="Address is mandatory";
    $flag=1;

  }
  else{

    $address=test_input($_POST["address"]);
  
    }
    
  

   
  

  if(empty($_POST["Phonenumber"])){
    $phnoerr="Phone number is mandatory";
    $flag=1;

  }
  else{

    $phno=test_input($_POST["Phonenumber"]);
    if(!preg_match('/^[0-9]{10}+$/',$phno)){
      $phnoerr="Invalid Phone number";
      $flag=1;
    }
    
   
  }


 
  if($_POST['state']=="Select an option" || $_POST['state']=="")
  {
   $stateerr="Please choose a state";
   $flag=1;
  }
  else{
   $state=$_POST['state'];
  }

   


  
  if(empty($_POST["spassword"])){
    $spasserr="Please create a password";
    $flag=1;

  }
  else{


    $spass=test_input($_POST["spassword"]);

    if(strlen($spass)<'8'){
        $spasserr .="Your password Must contain atleast  8 digits !"."<br>";
        $flag=1;

  
        
    }

    if(!preg_match("#[0-9]+#" ,$spass)){
      $spasserr .="Your password Must contain atleast  1 number !"."<br>";
      $flag=1;

    }
    if(!preg_match("#[A-Z]+#",$spass)){
      $spasserr .="Your password Must contain atleast  1 Capital letter !"."<br>";
      $flag=1;

    }
    if(!preg_match("#[a-z]+#" ,$spass)){
      $spasserr .="Your password Must contain atleast  1 Small letter !"."<br>";
      $flag=1;

    }
    if(!preg_match('/[\'\/~`\!@#\$%\^&\*\(\)_\-\+=\{\}\[\]\|;:"\<\>,\.\?\\\]/' ,$spass)){
      $spasserr .="Your password Must contain atleast  1 Special characters!"."<br>";
      $flag=1;

    }


}

if(empty($_POST["conpassword"])){
  $cpasserr="Please create a password";

}
else{

  $cpass=test_input($_POST["conpassword"]);

   if(!($spass===$cpass))
   {
     $cpasserr="The passwords dont match";
	 $flag=1;
   }

}

$sqlall="SELECT * FROM `member` WHERE `Email`='$email' OR `Password`='$cpass'";
$queryall=mysqli_query($conn,$sqlall);
$rowcountall=mysqli_num_rows($queryall);

if($rowcountall==1)
{
  $flag=1;
  echo "<script> alert('This email or password is already in use! Please fill the details again.  '); </script>";
}

  
 if($flag==0)
	{
	$sql="INSERT INTO `member`(`Member_id`, `Member name`, `Email`, `Phone number`, `Address`, `State`,`Selling Quantity`,`Password`) VALUES ('','$fname $lname','$email','$phno','$address','$state','','$cpass')";

	$result=mysqli_query($conn,$sql);
	}



    if($result)
    {

      echo'<script>alert("Signed up successfully"); 
       window.location="http://localhost/major%20project/login.php";
       </script>';
      
       
    }
    else
    {
       echo'<script>alert("Failed to  sign up "); </script>';
    }
   
   

}




?>
